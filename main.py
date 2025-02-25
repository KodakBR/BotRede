import asyncio
import os
from dotenv import load_dotenv
from network_monitor import NetworkMonitor
from discord_notifier import DiscordNotifier
from web_interface import WebInterface
import threading

load_dotenv()

class NetworkMonitorBot:
    def __init__(self):
        # Inicializa os componentes
        self.network_monitor = NetworkMonitor(
            scan_interval=int(os.getenv('SCAN_INTERVAL', 300)),
            port_scan_timeout=int(os.getenv('PORT_SCAN_TIMEOUT', 2)),
            scan_common_ports=os.getenv('PORT_SCAN_COMMON', 'True').lower() == 'true'
        )
        self.discord_notifier = DiscordNotifier()
        self.web_interface = WebInterface(self.network_monitor)

    async def monitor_network(self):
        """Loop contínuo de monitoramento de rede."""
        while True:
            # Obtém as mudanças na rede
            new_devices, disconnected_devices, changed_devices = await self.network_monitor.get_network_changes()

            # Atualiza os eventos na interface web
            for device in new_devices:
                self.web_interface.add_event("Novo Dispositivo Conectado", device, 'low')
            for device in disconnected_devices:
                self.web_interface.add_event("Dispositivo desconectado", device, 'low')
            for device in changed_devices:
                risk_level = 'low'
                for port in device.get('ports', []):
                    if port['risk_level'] == 'high':
                        risk_level = 'high'
                        break
                    elif port['risk_level'] == 'medium':
                        risk_level = 'medium'
                self.web_interface.add_event("Port Changes Detected", device, risk_level)

            # Envia notificações do Discord
            await self.discord_notifier.notify_network_changes(
                new_devices, disconnected_devices, changed_devices
            )

            # Aguarda o próximo intervalo de varredura
            await asyncio.sleep(self.network_monitor.scan_interval)

    def start_web_interface(self):
        """Inicia a interface web em uma thread separada."""
        self.web_interface.run()

    async def start(self):
        """Inicia todos os componentes do bot de monitoramento de rede."""
        # Inicia a interface web em uma thread separada
        web_thread = threading.Thread(target=self.start_web_interface)
        web_thread.daemon = True
        web_thread.start()

        # Inicia o monitoramento de rede
        await self.monitor_network()

if __name__ == '__main__':
    bot = NetworkMonitorBot()
    try:
        # Inicia o cliente Discord e o monitoramento de rede
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(bot.discord_notifier.start())
        loop.create_task(bot.start())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nDesligando...")
    finally:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.discord_notifier.stop())
        loop.close()