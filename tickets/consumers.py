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

    # Esta função é chamada quando o servidor quer enviar um alerta para o navegador
    async def enviar_alerta(self, event):
        mensagem = event['mensagem']
        tipo_alerta = event.get('tipo', 'info')

        # Envia a mensagem de volta para o navegador em formato JSON
        await self.send(text_data=json.dumps({
            'mensagem': mensagem,
            'tipo': tipo_alerta
        }))