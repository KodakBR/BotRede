import discord
import asyncio
import os
from typing import Dict, List
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

class DiscordNotifier:
    def __init__(self):
        self.token = os.getenv('DISCORD_TOKEN')
        self.user_id = int(os.getenv('DISCORD_USER_ID'))
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = False  # Disable members intent since we don't need it
        intents.presences = False  # Disable presences intent since we don't need it
        self.client = discord.Client(intents=intents)
        self._setup_logging()
        self._setup_client()

    def _setup_logging(self):
        self.logger = logging.getLogger('DiscordNotifier')

    def _setup_client(self):
        @self.client.event
        async def on_ready():
            self.logger.info(f'Bot do Discord conectado como {self.client.user}')
            await self._cleanup_messages()

        @self.client.event
        async def on_message(message):
            if not self.client.is_ready():
                return
            if message.author.id == self.user_id and message.content.lower() == '/clear':
                await self._cleanup_messages()
                await message.delete()
                self.logger.info(f'Limpeza manual acionada pelo usuário {message.author}')

    async def start(self):
        """Inicia o cliente do Discord."""
        await self.client.start(self.token)

    async def stop(self):
        """Para o cliente do Discord."""
        await self.client.close()

    async def _cleanup_messages(self):
        """Apaga mensagens anteriores do bot ao iniciar ou quando o comando /clear é usado."""
        try:
            user = await self.client.fetch_user(self.user_id)
            if not user:
                self.logger.error(f"Não foi possível encontrar o usuário com ID {self.user_id}")
                return

            deleted_count = 0
            dm_channel = user.dm_channel
            if not dm_channel:
                dm_channel = await user.create_dm()

            async for message in dm_channel.history(limit=100):
                if message.author == self.client.user:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # Adiciona atraso para evitar limite de taxa
            
            if deleted_count > 0:
                self.logger.info(f"Limpeza de {deleted_count} mensagens do bot concluída com sucesso")
                confirmation = await user.send(f"✅ Mensagens limpas: {deleted_count}")
                await asyncio.sleep(5)
                await confirmation.delete()
            else:
                self.logger.info("Nenhuma mensagem para limpar")
                confirmation = await user.send("✨ Nenhuma mensagem para limpar")
                await asyncio.sleep(5)
                await confirmation.delete()

        except Exception as e:
            self.logger.error(f"Erro ao limpar mensagens: {e}")

    async def send_alert(self, alert_type: str, devices: List[Dict], risk_level: str = 'low'):
        """Envia um alerta para o usuário do Discord usando embeds."""
        try:
            user = await self.client.fetch_user(self.user_id)
            if not user:
                self.logger.error(f"Não foi possível encontrar o usuário com ID {self.user_id}")
                return

            risk_emoji = '🔴' if risk_level == 'high' else '🟡' if risk_level == 'medium' else '🟢'
            timestamp = datetime.now()
            
            for device in devices:
                # Cria embed com cor baseada no nível de risco
                embed = discord.Embed(
                    title=f"{risk_emoji} Alerta de Rede: {alert_type}",
                    color=0xFF0000 if risk_level == 'high' else 0xFFFF00 if risk_level == 'medium' else 0x00FF00,
                    timestamp=timestamp
                )

                # Adiciona informações do dispositivo
                embed.add_field(
                    name="📱 Informações do Dispositivo",
                    value=f"🌐 **Endereço IP:** {device['ip']}\n📍 **Endereço MAC:** {device['mac']}",
                    inline=False
                )

                # Adiciona informações das portas se disponível
                if 'ports' in device and device['ports']:
                    ports_info = ""
                    for port in device['ports']:
                        port_emoji = '🔴' if port['risk_level'] == 'high' else '🟡' if port['risk_level'] == 'medium' else '🟢'
                        risk_text = '⚠️ ALTO RISCO' if port['risk_level'] == 'high' else '⚠️ Risco Médio' if port['risk_level'] == 'medium' else '✅ Baixo Risco'
                        ports_info += f"{port_emoji} Porta **{port['port']}** - {port['service']}\n   └─ {risk_text}\n"
                    
                    if ports_info:
                        embed.add_field(
                            name="🔍 Portas Abertas",
                            value=ports_info,
                            inline=False
                        )

                # Adiciona rodapé com timestamp
                embed.set_footer(text="Horário da Detecção")
                
                await user.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Erro ao enviar alerta do Discord: {e}")

    async def notify_network_changes(self, new_devices: List[Dict], disconnected_devices: List[Dict], changed_devices: List[Dict]):
        """Envia notificações sobre mudanças na rede."""
        if new_devices:
            await self.send_alert("Novo Dispositivo Conectado", new_devices, 'low')

        if disconnected_devices:
            await self.send_alert("Dispositivo Desconectado", disconnected_devices, 'low')

        if changed_devices:
            for device in changed_devices:
                risk_level = 'low'
                for port in device.get('ports', []):
                    if port['risk_level'] == 'high':
                        risk_level = 'high'
                        break
                    elif port['risk_level'] == 'medium':
                        risk_level = 'medium'
                await self.send_alert("Alterações de Porta Detectadas", [device], risk_level)