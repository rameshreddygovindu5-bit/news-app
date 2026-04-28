import socket

target_ip = "32.193.27.142"
target_port = 5432

print(f"Checking port {target_port} on {target_ip}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
result = sock.connect_ex((target_ip, target_port))

if result == 0:
    print("Port is OPEN")
else:
    print(f"Port is CLOSED (Error code: {result})")
sock.close()
