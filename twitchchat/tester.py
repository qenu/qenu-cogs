from socket import socket


class TwitchChat:

    def __init__(self, channel_name: str, bot_name: str, auth: str = None):
        # these may change in the future
        server = 'irc.twitch.tv'
        port = 6667

        self.socket = socket()
        self.channel = channel_name
        self.socket.connect((server, port))

        self.allowed_to_post = auth or bot_name

        if self.allowed_to_post:
            self.socket.send(f'PASS {auth}\nNICK {bot_name}\n JOIN #{channel_name}\n'.encode())
        else:
            self.socket.send(f"NICK {bot_name}\n".encode('utf-8'))
            self.socket.send(f"JOIN #{channel_name}\n".encode('utf-8'))

        loading = True
        while loading:
            read_buffer_join = self.socket.recv(1024)
            read_buffer_join = read_buffer_join.decode()
            print (read_buffer_join)

            for line in read_buffer_join.split('\n')[0:-1]:
                # checks if loading is complete
                loading = 'End of /NAMES list' not in line

    def send_to_chat(self, message: str):
        """
        sends a message to twitch chat if it's possible
        :param message: message to send in twitch chat
        :return:
        """

        if self.allowed_to_post:
            message_temp = f'PRIVMSG #{self.channel} :{message}'
            self.socket.send(f'{message_temp}\n'.encode())
        else:
            raise RuntimeError('Bot has no permission to sent messages get auth token at http://twitchapps.com/tmi/')

    def listen_to_chat(self) -> tuple((str, str)):
        """
        listens to chat and returns name and
        designed for endless loops with ping pong socket concept
        :return: user, message from chat or None
        """
        read_buffer = self.socket.recv(1024).decode()
        for line in read_buffer.split('\r\n'):
            # ping pong to stay alive
            if 'PING' in line and 'PRIVMSG' not in line:
                self.socket.send('PONG tmi.twitch.tv\r\n'.encode())

            # reacts at user message
            elif line != '':
                parts = line.split(':', 2)
                return parts[1].split('!', 1)[0], parts[2]


if __name__ == "__main__":
    import asyncio
    CHANNEL_NAME = "salmoninthebox"
    INSTANCE_NAME = "blehhh"
    OAUTH = "oauth:9mi0z46ur9b90vn7n5moih9i362j3a"
    tw_chat = TwitchChat(auth=OAUTH, bot_name=INSTANCE_NAME, channel_name=CHANNEL_NAME)
    print ("connected to twitch chat")

    async def listener():
        tw_chat.send_to_chat(message="ㄍ")
        while True:
            user, message = tw_chat.listen_to_chat()
            print (f"{user} says: {message}")
            await asyncio.sleep(2)

    loop = asyncio.get_event_loop()
    print (f"{INSTANCE_NAME} started listening to {CHANNEL_NAME}")
    loop.run_until_complete(listener())
    print ("end of script")


    # loop.stop()