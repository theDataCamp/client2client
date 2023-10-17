import socket
import threading
import datetime
import tkinter as tk
from tkinter import scrolledtext, ttk

LOG_FILENAME = "broker_log.txt"
clients = []

class BrokerServer:
    def __init__(self, message_callback, client_conn_callback, client_disconn_callback):
        self.listen_port = 12345
        self.next_client_id = 1
        self.message_callback = message_callback
        self.client_conn_callback = client_conn_callback
        self.client_disconn_callback = client_disconn_callback
        self.server_stop_event = threading.Event()
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_socket.bind(('0.0.0.0', self.listen_port))
        self.listen_socket.listen(5)

    def log_message(self, client_id, message):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} [Client {client_id}]: {message}\n"
        with open(LOG_FILENAME, "a") as log_file:
            log_file.write(log_entry)
        self.message_callback(log_entry)

    def broadcast_message(self, sender_socket, message):
        for client in clients:
            if client != sender_socket:
                try:
                    client.send(message.encode())
                except:
                    client.close()
                    clients.remove(client)

    def handle_client(self, client_socket, client_id, address):
        self.client_conn_callback(client_id, address)
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                decoded_data = data.decode('utf-8', errors='replace')
                self.log_message(client_id, decoded_data)
                self.broadcast_message(client_socket, decoded_data)
        except Exception as e:
            print(f"Error with client {client_id}: {e}")
        finally:
            if client_socket in clients:  # Check if socket is in list before removing
                client_socket.close()
                clients.remove(client_socket)
            self.client_disconn_callback(client_id)

    def start(self):
        while not self.server_stop_event.is_set():
            try:
                self.listen_socket.settimeout(1)  # Set a timeout so we can periodically check if we should stop
                client_socket, address = self.listen_socket.accept()
                clients.append(client_socket)
                threading.Thread(target=self.handle_client, args=(client_socket, self.next_client_id, address)).start()
                self.next_client_id += 1
            except socket.timeout:
                pass

        # Clean up after stopping
        self.listen_socket.close()
        for client in clients:
            client.close()
        clients.clear()

    def stop(self):
        self.server_stop_event.set()

class MessagePanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.init_gui()

    def init_gui(self):
        lbl_title = tk.Label(self, text="Broker Server", font=("Arial", 18))
        lbl_title.pack(pady=10)

        self.msg_panel = scrolledtext.ScrolledText(self, width=60, height=10)
        self.msg_panel.pack(pady=10)

        btn_clear = tk.Button(self, text="Clear Messages", command=self.clear_messages)
        btn_clear.pack(pady=10)

    def display_message(self, message):
        self.msg_panel.insert(tk.END, message)
        self.msg_panel.see(tk.END)

    def clear_messages(self):
        self.msg_panel.delete(1.0, tk.END)

class ClientsPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.init_gui()

    def init_gui(self):
        lbl_clients = tk.Label(self, text="Connected Clients", font=("Arial", 14))
        lbl_clients.pack(pady=10)

        columns = ("Client ID", "IP Address", "Port")
        self.clients_tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.clients_tree.heading(col, text=col)
        self.clients_tree.pack(pady=10)

    def add_client(self, client_id, address):
        self.clients_tree.insert("", tk.END, values=(client_id, address[0], address[1]))

    def remove_client(self, client_id):
        for item in self.clients_tree.get_children():
            if self.clients_tree.item(item)['values'][0] == client_id:
                self.clients_tree.delete(item)
                break

class BrokerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Broker Server GUI")

        self.server_running = False
        self.server = None

        self.message_panel = MessagePanel(master)
        self.message_panel.pack(padx=10, pady=10, fill=tk.BOTH)

        self.clients_panel = ClientsPanel(master)
        self.clients_panel.pack(padx=10, pady=10, fill=tk.BOTH)

        self.btn_start_stop = tk.Button(master, text="Start Server", command=self.toggle_server)
        self.btn_start_stop.pack(pady=10)

        # Handle app close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_server(self):
        if not self.server_running:
            self.server = BrokerServer(
                self.message_panel.display_message,
                self.clients_panel.add_client,
                self.clients_panel.remove_client
            )
            threading.Thread(target=self.server.start).start()
            self.server_running = True
            self.btn_start_stop.config(text="Stop Server")
        else:
            self.server.stop()  # Stop the server and close all connections
            self.server_running = False
            self.btn_start_stop.config(text="Start Server")

    def on_closing(self):
        if self.server_running:
            self.server.stop()  # Stop the server and close all connections
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x680")
    app = BrokerGUI(root)
    root.mainloop()
