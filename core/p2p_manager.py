import socket
import threading
import json

class P2PManager:
    def __init__(self, config_manager, tailscale_manager, on_request_received_callback=None):
        self.config_manager = config_manager
        self.tailscale_manager = tailscale_manager
        self.on_request_received_callback = on_request_received_callback
        self.server_socket = None
        self.is_running = False
        self.port = 25562

    def start_server(self):
        if self.is_running:
            return
        self.is_running = True
        threading.Thread(target=self._server_loop, daemon=True).start()

    def stop_server(self):
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def _server_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(5)
        except Exception as e:
            print(f"[P2P] Server bind failed: {e}")
            self.is_running = False
            return

        while self.is_running:
            try:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client_sock, addr):
        client_sock.settimeout(35.0) # Allow up to 35 seconds for user choice prompt
        try:
            data = client_sock.recv(4096).decode('utf-8', errors='ignore')
            if not data:
                client_sock.close()
                return
            
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "friend_request":
                username = payload.get("username", "Unknown")
                acc_type = payload.get("account_type", "Offline")
                ip = payload.get("ip", addr[0])
                
                # Prevent self-requests
                my_username = self.config_manager.get("username", "")
                my_ip = self.tailscale_manager.get_ipv4()
                if username.lower() == my_username.lower() or ip == my_ip:
                    client_sock.sendall(json.dumps({"status": "self_request"}).encode('utf-8'))
                    client_sock.close()
                    return

                # Check duplicate
                friends = self.config_manager.get("friends", [])
                already_exists = False
                for f in friends:
                    if f.get("username").lower() == username.lower():
                        already_exists = True
                        break
                
                if already_exists:
                    client_sock.sendall(json.dumps({"status": "already_friends"}).encode('utf-8'))
                    client_sock.close()
                    return
                
                # Trigger callback
                if self.on_request_received_callback:
                    accepted = self.on_request_received_callback(username, acc_type, ip)
                    if accepted:
                        # Save friend
                        friends.append({
                            "username": username,
                            "account_type": acc_type,
                            "ip_address": ip,
                            "notes": "Added via request"
                        })
                        self.config_manager.set("friends", friends)
                        client_sock.sendall(json.dumps({"status": "accepted"}).encode('utf-8'))
                    else:
                        client_sock.sendall(json.dumps({"status": "declined"}).encode('utf-8'))
                else:
                    client_sock.sendall(json.dumps({"status": "declined"}).encode('utf-8'))
            client_sock.close()
        except Exception as e:
            print(f"[P2P] Error handling connection: {e}")
            try:
                client_sock.close()
            except Exception:
                pass

    def send_friend_request(self, target_ip, my_username, my_acc_type, my_ip):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(6.0) # Connection timeout
            client.connect((target_ip, self.port))
            
            payload = {
                "action": "friend_request",
                "username": my_username,
                "account_type": my_acc_type,
                "ip": my_ip
            }
            
            client.sendall(json.dumps(payload).encode('utf-8'))
            
            # Response socket timeout (wait up to 35 seconds for them to click yes/no)
            client.settimeout(40.0)
            resp_data = client.recv(1024).decode('utf-8', errors='ignore')
            client.close()
            
            if resp_data:
                resp = json.loads(resp_data)
                return resp.get("status", "unknown")
            return "no_response"
        except socket.timeout:
            return "timeout"
        except Exception:
            return "offline"
