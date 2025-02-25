import scapy.all as scapy
import nmap
import netifaces
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import asyncio
from collections import defaultdict
import statistics

class NetworkMonitor:
    def __init__(self, scan_interval: int = 300, port_scan_timeout: int = 2, scan_common_ports: bool = True):
        self.scan_interval = scan_interval
        self.port_scan_timeout = port_scan_timeout
        self.scan_common_ports = scan_common_ports
        self.known_devices: Dict[str, dict] = {}
        self.nm = nmap.PortScanner()
        self._setup_logging()
        
        # Atributos para análise de tráfego e detecção de anomalias
        self.traffic_history = defaultdict(list)  # Histórico de tráfego por IP
        self.baseline_traffic = {}  # Padrões normais de tráfego
        self.anomaly_thresholds = {
            'traffic_spike': 2.0,  # Multiplicador para picos de tráfego
            'port_scan_attempts': 5,  # Número de tentativas de varredura de porta
            'connection_frequency': 10  # Conexões por minuto
        }

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('network_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('NetworkMonitor')

    def get_network_interface(self) -> Optional[Tuple[str, str]]:
        """Obtém a interface de rede primária e seu endereço IP."""
        try:
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if not ip.startswith('127.'):
                            return interface, ip
        except Exception as e:
            self.logger.error(f"Erro ao obter interface de rede: {e}")
        return None

    async def scan_network(self) -> List[dict]:
        """Escaneia a rede em busca de dispositivos conectados."""
        try:
            interface_info = self.get_network_interface()
            if not interface_info:
                self.logger.error("Nenhuma interface de rede adequada encontrada")
                return []

            interface, ip = interface_info
            network = '.'.join(ip.split('.')[:-1]) + '.0/24'

            # Escaneamento ARP para descobrir dispositivos
            arp_request = scapy.ARP(pdst=network)
            broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast/arp_request
            answered_list = scapy.srp(arp_request_broadcast, timeout=3, verbose=False)[0]

            devices = []
            for element in answered_list:
                ports = await self.scan_ports_async(element[1].psrc) if self.scan_common_ports else []
                device = {
                    'ip': element[1].psrc,
                    'mac': element[1].hwsrc,
                    'timestamp': datetime.now().isoformat(),
                    'ports': ports
                }
                devices.append(device)

            return devices

        except Exception as e:
            self.logger.error(f"Erro ao escanear rede: {e}")
            return []

    async def scan_ports_async(self, ip: str) -> List[dict]:
        """Versão assíncrona do scanner de portas para melhor eficiência."""
        try:
            if self.scan_common_ports:
                ports = '20-23,25,53,80,110,143,443,445,3389'
            else:
                ports = '1-1024'

            # Usa asyncio para executar o nmap de forma não bloqueante
            process = await asyncio.create_subprocess_exec(
                'nmap', '-sT', '-T4', f'--host-timeout={self.port_scan_timeout}s',
                '-p', ports, ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            open_ports = []
            if process.returncode == 0:
                # Processa a saída do nmap
                for line in stdout.decode().split('\n'):
                    if 'open' in line and 'tcp' in line:
                        parts = line.split()
                        port = int(parts[0].split('/')[0])
                        service = parts[2] if len(parts) > 2 else 'unknown'
                        open_ports.append({
                            'port': port,
                            'service': service,
                            'risk_level': self.assess_port_risk(port, service)
                        })

            return open_ports

        except Exception as e:
            self.logger.error(f"Erro ao escanear portas para {ip}: {e}")
            return []

    def analyze_traffic(self, ip: str, packet_count: int, packet_size: int) -> Dict:
        """Analisa o tráfego de rede para um IP específico."""
        timestamp = datetime.now()
        traffic_data = {
            'timestamp': timestamp,
            'packet_count': packet_count,
            'packet_size': packet_size
        }
        
        # Adiciona dados ao histórico
        self.traffic_history[ip].append(traffic_data)
        
        # Mantém apenas as últimas 24 horas de dados
        cutoff = timestamp - timedelta(hours=24)
        self.traffic_history[ip] = [d for d in self.traffic_history[ip] if d['timestamp'] > cutoff]
        
        return self.detect_anomalies(ip)

    def detect_anomalies(self, ip: str) -> Dict:
        """Detecta anomalias no tráfego de rede."""
        if not self.traffic_history[ip]:
            return {'anomalies': []}

        recent_traffic = self.traffic_history[ip][-10:]  # Últimas 10 amostras
        packet_counts = [d['packet_count'] for d in recent_traffic]
        packet_sizes = [d['packet_size'] for d in recent_traffic]

        anomalies = []

        # Calcula estatísticas
        avg_count = statistics.mean(packet_counts)
        std_count = statistics.stdev(packet_counts) if len(packet_counts) > 1 else 0
        avg_size = statistics.mean(packet_sizes)
        std_size = statistics.stdev(packet_sizes) if len(packet_sizes) > 1 else 0

        # Detecta picos de tráfego
        current_count = packet_counts[-1]
        if current_count > avg_count + (std_count * self.anomaly_thresholds['traffic_spike']):
            anomalies.append({
                'type': 'traffic_spike',
                'severity': 'high',
                'description': f'Pico anormal de tráfego detectado: {current_count} pacotes'
            })

        # Detecta padrões suspeitos de varredura de porta
        port_scan_count = sum(1 for d in recent_traffic if d['packet_count'] > avg_count * 2)
        if port_scan_count >= self.anomaly_thresholds['port_scan_attempts']:
            anomalies.append({
                'type': 'port_scan',
                'severity': 'high',
                'description': 'Possível tentativa de varredura de porta detectada'
            })

        return {
            'anomalies': anomalies,
            'stats': {
                'avg_packet_count': avg_count,
                'avg_packet_size': avg_size,
                'std_packet_count': std_count,
                'std_packet_size': std_size
            }
        }

    def assess_port_risk(self, port: int, service: str) -> str:
        """Avalia o nível de risco de uma porta aberta."""
        high_risk_ports = {21, 22, 23, 3389}  # FTP, SSH, Telnet, RDP
        medium_risk_ports = {80, 443, 8080, 8443}  # HTTP, HTTPS
        high_risk_services = {'telnet', 'ftp', 'rpc'}

        if port in high_risk_ports or service.lower() in high_risk_services:
            return 'high'
        elif port in medium_risk_ports:
            return 'medium'
        return 'low'

    async def get_network_changes(self) -> Tuple[List[dict], List[dict], List[dict]]:
        """Detecta mudanças na rede."""
        current_devices = {device['ip']: device for device in await self.scan_network()}
        
        new_devices = []
        disconnected_devices = []
        changed_devices = []

        # Verifica novos dispositivos e alterações
        for ip, device in current_devices.items():
            if ip not in self.known_devices:
                new_devices.append(device)
            else:
                # Verifica mudanças nas portas
                old_ports = {p['port'] for p in self.known_devices[ip].get('ports', [])}
                new_ports = {p['port'] for p in device.get('ports', [])}
                if old_ports != new_ports:
                    changed_devices.append(device)

        # Verifica dispositivos desconectados
        for ip in self.known_devices:
            if ip not in current_devices:
                disconnected_devices.append(self.known_devices[ip])

        # Atualiza dispositivos conhecidos
        self.known_devices = current_devices

        return new_devices, disconnected_devices, changed_devices