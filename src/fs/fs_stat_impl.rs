use std::ffi::CString;
use std::mem::MaybeUninit;
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

use nfs_mamont::auth::Credential;
use nfs_mamont::vfs::fs_stat;

use super::MirrorFS;

impl fs_stat::FsStat for MirrorFS {
    async fn fs_stat(
        &self,
        args: fs_stat::Args,
        _cred: &Credential,
    ) -> Result<fs_stat::Success, fs_stat::Fail> {
        let path = match self.path_for_handle(&args.root).await {
            Ok(path) => path,
            Err(error) => return Err(fs_stat::Fail { error, root_attr: None }),
        };

        // Report real stats of export's underlying FS.
        // Some tests rely on `df`, and it hides zero sized FSs in output
        let stat = match statvfs(&path) {
            Ok(stat) => stat,
            Err(error) => {
                return Err(fs_stat::Fail {
                    error: Self::io_error_to_vfs(&error),
                    root_attr: Self::file_attr(&path),
                })
            }
        };
        let block_size = stat.f_frsize as u64;
        Ok(fs_stat::Success {
            root_attr: Self::file_attr(&path),
            total_bytes: stat.f_blocks as u64 * block_size,
            free_bytes: stat.f_bfree as u64 * block_size,
            available_bytes: stat.f_bavail as u64 * block_size,
            total_files: stat.f_files as u64,
            free_files: stat.f_ffree as u64,
            available_files: stat.f_favail as u64,
            invarsec: 0,
        })
    }
}

fn statvfs(path: &Path) -> std::io::Result<libc::statvfs> {
    let path = CString::new(path.as_os_str().as_bytes())?;
    let mut stat = MaybeUninit::<libc::statvfs>::uninit();
    // SAFETY: `path` is NUL-terminated and `stat` points to writable memory of the right size.
    if unsafe { libc::statvfs(path.as_ptr(), stat.as_mut_ptr()) } != 0 {
        return Err(std::io::Error::last_os_error());
    }
    // SAFETY: statvfs returned 0, so it filled `stat`.
    Ok(unsafe { stat.assume_init() })
}
