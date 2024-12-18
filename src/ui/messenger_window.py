import sys
import os
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QInputDialog
from PyQt5.QtCore import QMutex, Qt
from .new_design import Ui_BlockChain
from crypto.encryption import SymmetricEncryption


class MessengerApp(QMainWindow, Ui_BlockChain):
    """
    A messenger application with chat management, message sending, and window resizing capabilities
    """

    update_message_area_signal = QtCore.pyqtSignal(str)

    def __init__(self, username: str, cbu, smsg, rmvcn, p2p_network, dh_key_manager, blockchain):
        """
        Initializes the messenger application, sets up the UI, loads chat names,
        styles, and message templates, and connects signals to their respective slots
        """
        super().__init__()

        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.username = username

        bubbles_file = "src/ui/formats.html"
        self.templates = self.load_message_bubbles(bubbles_file)
        self.update_message_area_signal.connect(self.update_message_area)

        self.border_width = 5
        self.is_resizing = False
        self.resize_direction = None
        self.closed = False

        self.p2p_network = p2p_network
        self.cbu = cbu
        self.smsg = smsg
        self.rmvcn = rmvcn
        self.dh_key_manager = dh_key_manager
        self.blockchain = blockchain
        self.message_area_mutex = QMutex()
        self.chat_names = [peer[2] for peer in self.p2p_network.peers]
        self.load_chats()

        self.chatList.itemClicked.connect(self.select_chat)

        self.sendMessage_button.clicked.connect(self.send_message)
        self.messagePrint_area.returnPressed.connect(self.send_message)
        self.close_button.clicked.connect(self.close_window)
        self.minimize_button.clicked.connect(self.minimize_window)
        self.maximize_button.clicked.connect(self.maximize_window)
        self.addChatAction.triggered.connect(self.add_chat)
        self.renameChatAction.triggered.connect(self.rename_chat)
        self.deleteChatAction.triggered.connect(self.delete_chat)
        self.changeNicknameAction.triggered.connect(self.change_nickname)
        self.chat_Search.textChanged.connect(self.search_chats)
        self.showPeersAction.triggered.connect(self.show_peers_dialog)

        #self.work_exemp = work_exemp

    def add_chat(self):
        """
        Adds a new chat by prompting the user to enter a chat name

        If the user provides a valid name, it is added to the list of chats
        and the chat list is updated
        """
        text, ok = QtWidgets.QInputDialog.getText(
            self.centralwidget, "Add Chat", "Enter chat name:"
        )
        if ok and text.strip():
            if self.cbu(text.strip()):
                self.chat_names.append(text.strip())
            # messages = self.rcvmsg()
            self.load_chats()

    def delete_chat(self):
        """
        Deletes the selected chat from the chat list

        If no chat is selected, a warning message is shown
        Otherwise, the selected chat is removed and the list is updated
        """
        selected_items = self.chatList.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(
                self.centralwidget, "No Selection", "Please select a chat to delete."
            )
            return

        for item in selected_items:
            self.chat_names.remove(item.text())
            # self.rmvcn(item.text())
        self.currentChatLabel.setText("Select chat")
        self.load_chats()

    def rename_chat(self):
        """
        Renames the selected chat

        If a chat is selected, the user is prompted to provide a new name
        The chat name is updated and the list of chats is refreshed
        """
        selected_items = self.chatList.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(
                self.centralwidget, "No Selection", "Please select a chat to rename."
            )
            return

        current_name = selected_items[0].text()
        new_name, ok = QtWidgets.QInputDialog.getText(
            self.centralwidget, "Rename Chat", f"Rename '{current_name}' to:"
        )
        if ok and new_name.strip():
            index = self.chat_names.index(current_name)
            self.chat_names[index] = new_name.strip()
            self.load_chats()

    def load_chats(self):
        """
        Loads and displays the list of chats in the chatList widget

        Each chat name from self.chat_names is added as an item in the list
        """
        self.chatList.clear()
        for chat_name in self.chat_names:
            item = QListWidgetItem(chat_name)
            self.chatList.addItem(item)

    def select_chat(self, item):
        """
        Selects a chat from the list and displays the selected chat's name
        in the currentChatLabel

        Clears the message area for the selected chat
        """
        chat_name = item.text()
        self.currentChatLabel.setText(chat_name)
        self.message_area.clear()
        peer_nickname = chat_name

        peer_key = None
        for peer in self.p2p_network.peers:
            if peer[2] == peer_nickname:
                peer_key = peer[3]
                break
        if peer_key:
            self.handle_messages(self.dh_key_manager.get_public_key(), peer_key)

    def send_message(self):
        """
        Sends a message from the messagePrint_area input field

        The message is added to the message area with a sender username and timestamp
        """
        text = self.messagePrint_area.text().strip()
        if text:
            time = datetime.now().strftime("%H:%M")
            bubble = self.templates["Sender Bubble"].format(
                time=time, username=self.username, text=text
            )

            username = self.currentChatLabel.text()
            if username in ('', 'Select chat', None):
                print('No chat selected!')
                return
            self.messagePrint_area.clear()

            self.smsg(username, text, self)

    def receive_message(self, sender, text):
        """
        Receives a message from another user and displays it in the message area

        The received message includes the sender's username and a timestamp
        """
        if text:
            time = datetime.now().strftime("%H:%M")
            bubble = self.templates["Receiver Bubble"].format(
                time=time, username=sender, text=text
            )

            current_html = self.message_area.toHtml()
            new_html = current_html + bubble
            self.message_area.setHtml(new_html)

    def get_messages(self, my_key, peer_key):
        messages = []
        for block in self.blockchain.chain:
            for transaction in block.transactions:
                if (
                    transaction.sender == my_key and transaction.recipient == peer_key
                ) or (
                    transaction.sender == peer_key and transaction.recipient == my_key
                ):
                    messages.append(transaction)
        for transaction in self.blockchain.pending_transactions:
            if (
                transaction.sender == my_key and transaction.recipient == peer_key
            ) or (transaction.sender == peer_key and transaction.recipient == my_key):
                messages.append(transaction)

        return messages


    @QtCore.pyqtSlot(str)
    def update_message_area(self, html):
        self.message_area.setHtml(html)
    def handle_messages(self, my_key, peer_key):
        sender_nickname = None
        for peer in self.p2p_network.peers:
            if peer[3] == peer_key:
                sender_nickname = peer[2]
                break
        if sender_nickname != self.currentChatLabel.text():
            return

        self.message_area.clear()
        current_html = self.message_area.toHtml()
        messages = self.get_messages(my_key, peer_key)
        for message in messages:
            time_mes = datetime.fromtimestamp(float(message.timestamp)).strftime("%H:%M")
            if my_key == message.sender:
                shared_key = self.dh_key_manager.generate_shared_key(message.recipient)
                encryptor = SymmetricEncryption(shared_key, algorithm="AES", mode="CBC")
                bubble = self.templates["Sender Bubble"].format(
                    time=time_mes, username=self.username,
                    text=encryptor.decrypt(bytes.fromhex(message.content))
                )
            else:
                shared_key = self.dh_key_manager.generate_shared_key(message.sender)
                encryptor = SymmetricEncryption(shared_key, algorithm="AES", mode="CBC")
                reciever = [peer for peer in self.p2p_network.peers if peer[3] == message.sender]
                bubble = self.templates["Receiver Bubble"].format(
                    time=time_mes, username=reciever[0][2],
                    text=encryptor.decrypt(bytes.fromhex(message.content))
                )
            current_html += bubble

        self.message_area_mutex.lock()
        try:
            QtCore.QMetaObject.invokeMethod(self, "update_message_area", Qt.QueuedConnection, QtCore.Q_ARG(str, current_html))
            # self.update_message_area_signal.emit(current_html)
        finally:
            self.message_area_mutex.unlock()


    def load_message_bubbles(self, file_path):
        """
        Loads message bubble templates from an HTML file

        Parses the file and stores the templates for use in displaying
        sent and received messages

        :param file_path: Path to the HTML file containing the message bubble templates
        :return: A dictionary of message bubble templates
        """
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        templates = {}
        sections = content.split("<!-- TEMPLATE:")
        for section in sections[1:]:
            marker, html = section.split("-->", 1)
            templates[marker.strip()] = html.strip()

        return templates

    def change_nickname(self):
        """
        Changes the user`s username (nickname)

        The new username is validated and updated accordingly
        """
        new_username, ok = QInputDialog.getText(
            self, "Change Nickname", "Enter new nickname:"
        )
        if ok and new_username.strip():
            self.username = new_username.strip()

    def close_window(self):
        """
        Closes the application window
        """
        self.closed = True
        self.close()

    def minimize_window(self):
        """
        Minimizes the application window
        """
        self.showMinimized()

    def maximize_window(self):
        """
        Maximizes the application window or restores it to its normal size
        """
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        """
        Handles mouse press events for window dragging and resizing

        The window can be dragged or resized based on the mouse position

        :param event: The mouse press event
        """
        if event.button() == QtCore.Qt.LeftButton:
            if self.up_stroke.geometry().contains(event.pos()):
                self.is_dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            else:
                self.is_resizing = True
                self.resize_direction = self.get_resize_direction(event.pos())
            event.accept()

    def mouseMoveEvent(self, event):
        """
        Handles mouse move events for window dragging and resizing

        The window will be moved or resized based on the mouse position

        :param event: The mouse move event
        """
        if getattr(self, "is_dragging", False):
            self.move(event.globalPos() - self.drag_position)
            event.accept()

        elif getattr(self, "is_resizing", False):
            self.resize_window(event.globalPos())
            event.accept()
        else:
            self.get_resize_direction(event.pos())

    def mouseReleaseEvent(self, event):
        """
        Handles mouse release events to stop dragging or resizing

        :param event: The mouse release event
        """
        self.is_dragging = False
        self.is_resizing = False
        self.resize_direction = None

    def get_resize_direction(self, pos):
        """
        Determines the resize direction based on the mouse position

        :param pos: The position of the mouse event
        :return: A string representing the direction of resizing
        """
        rect = self.rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        mx, my = pos.x(), pos.y()

        directions = {
            "top": my <= self.border_width,
            "bottom": my >= h - self.border_width,
            "left": mx <= self.border_width,
            "right": mx >= w - self.border_width,
        }
        direction = None
        if directions["top"] and directions["left"]:
            direction = "top_left"
        elif directions["top"] and directions["right"]:
            direction = "top_right"
        elif directions["bottom"] and directions["left"]:
            direction = "bottom_left"
        elif directions["bottom"] and directions["right"]:
            direction = "bottom_right"
        elif directions["top"]:
            direction = "top"
        elif directions["bottom"]:
            direction = "bottom"
        elif directions["left"]:
            direction = "left"
        elif directions["right"]:
            direction = "right"
        return direction

    def resize_window(self, global_pos):
        """
        Resizes the window based on the mouse position

        The window's size is adjusted based on the direction determined by the
        mouse position during resizing

        :param global_pos: The global position of the mouse
        """
        rect = self.frameGeometry()
        if self.resize_direction == "top":
            rect.setTop(global_pos.y())
        elif self.resize_direction == "bottom":
            rect.setBottom(global_pos.y())
        elif self.resize_direction == "left":
            rect.setLeft(global_pos.x())
        elif self.resize_direction == "right":
            rect.setRight(global_pos.x())
        elif self.resize_direction == "top_left":
            rect.setTopLeft(global_pos)
        elif self.resize_direction == "top_right":
            rect.setTopRight(global_pos)
        elif self.resize_direction == "bottom_left":
            rect.setBottomLeft(global_pos)
        elif self.resize_direction == "bottom_right":
            rect.setBottomRight(global_pos)
        self.setGeometry(rect)

    def test_receive_message(self):
        """
        Simulates the reception of a message

        This function was used only for testing recievers` bubbles,
        it is not utilizing in the actual app
        """
        sender = "Campot"
        text = "PUT UR PHONE DOWN!!!"
        self.receive_message(sender, text)

    def keyPressEvent(self, event):
        """
        Handles key press events for the application

        If the 'V' key is pressed, a test message is received for testing purposes

        :param event: The key press event
        """
        if event.key() == Qt.Key_V:
            self.test_receive_message()
            event.accept()
        else:
            super().keyPressEvent(event)

    def search_chats(self, text):
        """
        Searches for chats based on the text entered in the search field

        Filters the list of chats to show only those that match the search text

        :param text: The text to search for in chat names
        """
        self.chatList.clear()
        filtered_chats = [chat for chat in self.chat_names if text.lower() in chat.lower()]
        self.chatList.addItems(filtered_chats)

    def show_peers_dialog(self):
        """

        Shows avaliable peers
        """

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Available Peers")
        dialog.resize(300, 200)

        peer_list_widget = QtWidgets.QListWidget(dialog)
        peer_list_widget.setGeometry(10, 10, 280, 180)


        for peer in self.p2p_network.peers:
            item = QtWidgets.QListWidgetItem(peer[2])
            peer_list_widget.addItem(item)


        def on_peer_clicked(item):
            peer_name = item.text()
            QtWidgets.QMessageBox.information(self, "Peer Selected", f"You selected: {peer_name}")

        peer_list_widget.itemClicked.connect(on_peer_clicked)

        dialog.exec_()



if __name__ == "__main__":
    app = QApplication(sys.argv)

    with open("styles.qss", "r") as file:
        style_sheet = file.read()
        app.setStyleSheet(style_sheet)

    window = MessengerApp()
    window.show()
    sys.exit(app.exec_())
