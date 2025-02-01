# EAIS-downloader
Python script is designed for downloading files from a EAIS archive, processing the data based on provided identifiers, and saving the files to a local folder.

The script reads this configuration file at runtime, and if the file is not found or the values are missing, it falls back to the default values. 
The configuration file (eais.conf) contains the following key settings:

MAX_CONCURRENT_DOWNLOADS: Defines the maximum number of concurrent downloads allowed. This helps control the number of simultaneous threads used for downloading files.
Default: 4 (if not specified in the config file).

MAX_RETRY_COUNT: The number of retry attempts the script will make if a file download fails (e.g., due to a timeout or connection issue).
Default: 10 (if not specified in the config file).

DOWNLOAD_DIR: The directory where files will be saved after download. If not specified, it defaults to a temporary directory (e.g., C:\Temp on Windows) or the script's own directory.
Default: C:\Temp (if not specified in the config file).

Then, the user is prompted to input EAIS identifiers or URLs (either as command-line arguments or interactively).
For each identifier, the script fetches metadata, sanitizes the folder name, and attempts to download associated files (images) from a remote server.
The script supports concurrent downloads using a thread pool and tracks the download progress with a progress bar.
The downloaded files are organized into folders named after the data retrieved, and failed downloads are retried up to a specified limit.
The script ensures that the download process is robust and can handle issues such as timeouts or network errors by retrying the download multiple times if necessary.









