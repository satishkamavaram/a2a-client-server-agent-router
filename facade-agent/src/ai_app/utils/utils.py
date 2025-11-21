def get_base_url(url) -> str:
    if "?" in url:
        return url.split("?")[0]
    return url

def is_http_success_status(status_code) -> bool:
    if status_code:
        return 200 <= status_code <=299
    return False

def replace_newline_with_space(message) -> bool:
    if message:
        return message.replace("\n","")
    return message