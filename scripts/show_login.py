import sys
import webview

def main():
    if len(sys.argv) < 2:
        print("Usage: show_login.py <url>")
        return
        
    url = sys.argv[1]
    
    # Create webview window
    webview.create_window(
        title="Tailscale Login",
        url=url,
        width=500,
        height=650,
        resizable=False
    )
    # Start webview
    webview.start()

if __name__ == "__main__":
    main()
