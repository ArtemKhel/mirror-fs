use clap::Parser;
use std::io::ErrorKind;
use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::info;

use nfs_mamont::vfs::file::Path as VfsPath;
use nfs_mamont::{handle_forever, ServerContext};

use nfs_mamont_util::{MountService, NlmService, PoolAllocator};

pub mod args;
pub mod config;
pub mod fs;
pub mod fs_map;

pub mod auth;
#[cfg(test)]
mod tests;

#[tokio::main]
async fn main() -> std::io::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("nfs_mamont=debug")),
        )
        .init();

    let args = args::Args::parse();

    let config = config::load_config(&args.config_path)?;

    #[cfg(feature = "metrics")]
    init_metrics_exporter(config.metrics.unwrap_or_default().port);
    #[cfg(not(feature = "metrics"))]
    if config.metrics.is_some() {
        tracing::warn!(
            "config has a [metrics] section, but `metrics` feature is disabled; ignoring it"
        );
    }

    let root_squash = !args.no_root_squash;
    let fs = Arc::new(fs::MirrorFS::new(config.export_root.clone(), root_squash));

    let context = ServerContext::new(
        Arc::new(PoolAllocator::new(config.allocator.buffer_size, config.allocator.buffer_count)),
        config.vfs_pool_size,
    );
    let backend_id =
        context.add_backend(fs.clone()).expect("no free backend slot for the mirror file system");
    fs.set_backend_id(backend_id).await;

    info!(export_root = %config.export_root.display(), bind = %args.addr, "mirrorfs startup");

    let listener = TcpListener::bind(&args.addr).await?;

    let mount_service = Arc::new(MountService::new());

    for export in &config.exports {
        let root_handle = fs.handle_for_path(&export.local_path).await.map_err(|error| {
            std::io::Error::new(
                ErrorKind::InvalidInput,
                format!(
                    "failed to resolve export handle for {}: {error:?}",
                    export.local_path.display()
                ),
            )
        })?;

        mount_service.add_export(VfsPath::new(export.mount_path.clone())?, root_handle).await;
    }

    let nlm_service = Arc::new(NlmService::new());
    handle_forever(listener, context, mount_service, nlm_service).await
}

#[cfg(feature = "metrics")]
fn init_metrics_exporter(port: u16) {
    use metrics_exporter_prometheus::NativeHistogramConfig;
    metrics_exporter_prometheus::PrometheusBuilder::new()
        .set_native_histogram_for_metric(
            metrics_exporter_prometheus::Matcher::Prefix("nfsmamont_".to_string()),
            {
                let bucket_factor = 2.0;
                let max_buckets = 32;
                let zero_threshold = 0.0;
                NativeHistogramConfig::new(bucket_factor, max_buckets, zero_threshold).unwrap()
            },
        )
        .with_http_listener(([0, 0, 0, 0], port))
        .install()
        .expect("failed to install Prometheus recorder");

    tokio::spawn(
        tokio_metrics::RuntimeMetricsReporterBuilder::default()
            .with_interval(std::time::Duration::from_secs(1))
            .describe_and_run(),
    );
}
