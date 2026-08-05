import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificacaoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Quando o navegador tentar conectar, nós verificamos se o usuário está logado
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            # Colocamos o usuário em um "grupo" global de notificações
            self.grupo_nome = 'notificacoes_globais'
            await self.channel_layer.group_add(
                self.grupo_nome,
                self.channel_name
            )
            # Aceita a conexão WebSocket
            await self.accept()

    async def disconnect(self, close_code):
        # Quando o usuário fechar a aba do navegador, tiramos ele do grupo
        if hasattr(self, 'grupo_nome'):
            await self.channel_layer.group_discard(
                self.grupo_nome,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        # Responde ao 'ping' do heartbeat do cliente para manter a conexão
        # Redis/ASGI ativa. Mensagens vazias ou desconhecidas são ignoradas
        # para que o canal nunca engasgue com pacotes vazios.
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    # Esta função é chamada quando o servidor quer enviar um alerta para o navegador
    async def enviar_alerta(self, event):
        mensagem = event['mensagem']
        tipo_alerta = event.get('tipo', 'info')

        # Envia a mensagem de volta para o navegador em formato JSON
        await self.send(text_data=json.dumps({
            'mensagem': mensagem,
            'tipo': tipo_alerta,
            'ticket_id': event.get('ticket_id'),
        }))