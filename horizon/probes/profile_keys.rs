// Developer HTTPS probe for the pinned official horizon-server-files crate.
// No accounts, credentials or player sessions. See SERVER_TEST_RU.md.
fn main() {
    match horizon_server_files::profiles::fetch_profile_key_keys(
        &horizon_server_files::profiles::discovery_url(),
    ) {
        Ok(keys) => println!("official profile keys parsed: {}", keys.len()),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
