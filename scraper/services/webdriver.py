import os
import undetected_chromedriver as uc
def get_webdriver() -> uc.Chrome:
    # Create the temp_files directory if it doesn't exist
    download_dir = os.path.abspath("./temp_files")
    os.makedirs(download_dir, exist_ok=True)
    opts = uc.ChromeOptions()
    opts.add_argument('--ignore-ssl-errors=yes')
    opts.add_argument('--ignore-certificate-errors')
    # Setting download directory
    opts.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    prefs = {
        # Setting download directory
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        # Proxy
        "webrtc.ip_handling_policy" : "disable_non_proxied_udp",
        "webrtc.multiple_routes_enabled": False,
        "webrtc.nonproxied_udp_enabled" : False
    }
    opts.add_experimental_option("prefs", prefs)
    show_browser = False
    if not show_browser:
        # Add headless mode option
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")  # Disable GPU usage, recommended for headless mode
        opts.add_argument("--no-sandbox")  # Bypass OS security model, required for headless mode
        opts.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    # Initialize Chrome driver with a specific major version
    driver = uc.Chrome(options=opts, version_main=128)

    return driver
