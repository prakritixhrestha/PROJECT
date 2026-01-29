import urllib.request
import urllib.error

try:
    # Try to access the admin page
    response = urllib.request.urlopen('http://127.0.0.1:8000/admin/')
    print(f"Status Code: {response.status}")
    print(f"Success! Admin page is accessible")
    
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.reason}")
    print(f"Response body:")
    print(e.read().decode('utf-8')[:500])
    
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason}")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
