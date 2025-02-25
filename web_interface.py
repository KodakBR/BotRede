from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import os
from dotenv import load_dotenv
from collections import deque

load_dotenv()

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html class="dark">
<head>
    <title>Painel de Monitoramento de Rede</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script>
        // Immediately set the theme to avoid flash of wrong theme
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    </script>
</head>
<body class="bg-gray-100 dark:bg-gray-900 transition-colors duration-200">
    <div class="container mx-auto px-4 py-8">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800 dark:text-gray-100">Painel de Monitoramento de Rede</h1>
            <button id="themeToggle" class="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100">
                <span class="dark:hidden">🌙</span>
                <span class="hidden dark:inline">☀️</span>
            </button>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 transition-colors duration-200">
                <h2 class="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">Dispositivos Ativos</h2>
                <div id="deviceList" class="space-y-4">
                    <!-- Devices will be populated here -->
                </div>
            </div>
            
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 transition-colors duration-200">
                <h2 class="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">Eventos Recentes</h2>
                <div id="eventList" class="space-y-2">
                    <!-- Events will be populated here -->
                </div>
            </div>
        </div>
    </div>

    <script>
        // Theme toggle functionality
        const themeToggle = document.getElementById('themeToggle');
        
        function updateTheme(isDark) {
            if (isDark) {
                document.documentElement.classList.add('dark');
                localStorage.theme = 'dark';
            } else {
                document.documentElement.classList.remove('dark');
                localStorage.theme = 'light';
            }
        }

        themeToggle.addEventListener('click', () => {
            const isDark = !document.documentElement.classList.contains('dark');
            updateTheme(isDark);
        });

        // Initial theme setup
        updateTheme(localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches));

        // Dashboard update functionality
        function getRiskEmoji(riskLevel) {
            return riskLevel === 'high' ? '🔴' :
                   riskLevel === 'medium' ? '🟡' : '🟢';
        }

        function getRiskColorClass(riskLevel, isDark = false) {
            const baseClass = isDark ? 'dark:' : '';
            return riskLevel === 'high' ? `${baseClass}text-red-500` :
                   riskLevel === 'medium' ? `${baseClass}text-yellow-500` :
                   `${baseClass}text-green-500`;
        }

        function updateDashboard() {
            // Update devices
            fetch('/api/devices?page=1&limit=10')
                .then(response => response.json())
                .then(data => {
                    const deviceList = document.getElementById('deviceList');
                    deviceList.innerHTML = '';
                    
                    data.devices.forEach(device => {
                        const deviceElement = document.createElement('div');
                        deviceElement.className = 'bg-gray-50 dark:bg-gray-700 p-4 rounded-lg transition-colors duration-200';
                        
                        let portsHtml = '';
                        if (device.ports && device.ports.length > 0) {
                            portsHtml = '<div class="mt-2 space-y-1">';
                            device.ports.forEach(port => {
                                const riskEmoji = getRiskEmoji(port.risk_level);
                                const riskColorClass = getRiskColorClass(port.risk_level, true);
                                portsHtml += `
                                    <div class="${riskColorClass} text-sm">
                                        ${riskEmoji} Porta ${port.port} (${port.service})
                                    </div>`;
                            });
                            portsHtml += '</div>';
                        }
                        
                        deviceElement.innerHTML = `
                            <div class="font-semibold text-gray-800 dark:text-gray-100">${device.ip}</div>
                            <div class="text-sm text-gray-600 dark:text-gray-400">MAC: ${device.mac}</div>
                            ${portsHtml}
                        `;
                        deviceList.appendChild(deviceElement);
                    });
                });

            // Update events
            fetch('/api/events?page=1&limit=10')
                .then(response => response.json())
                .then(data => {
                    const eventList = document.getElementById('eventList');
                    eventList.innerHTML = '';
                    
                    data.events.forEach(event => {
                        const eventElement = document.createElement('div');
                        eventElement.className = 'p-2 rounded-lg bg-gray-50 dark:bg-gray-700 transition-colors duration-200';
                        const riskEmoji = getRiskEmoji(event.risk_level);
                        const riskColorClass = getRiskColorClass(event.risk_level, true);
                        eventElement.innerHTML = `
                            <div class="flex justify-between items-center">
                                <span class="${riskColorClass}">${riskEmoji} ${event.type}</span>
                                <span class="text-sm text-gray-600 dark:text-gray-400">${event.timestamp}</span>
                            </div>
                        `;
                        eventList.appendChild(eventElement);
                    });
                });
        }

        // Update dashboard every 10 seconds
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

class WebInterface:
    def __init__(self, network_monitor):
        self.network_monitor = network_monitor
        self.events = deque(maxlen=50)  # Keep only 50 most recent events
        self.setup_routes()

    def setup_routes(self):
        @app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)

        @app.route('/api/devices')
        def get_devices():
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            # Get only necessary device data
            devices = []
            for device in sorted(
                list(self.network_monitor.known_devices.values()),
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )[start_idx:end_idx]:
                filtered_device = {
                    'ip': device['ip'],
                    'mac': device['mac'],
                    'ports': [{
                        'port': p['port'],
                        'service': p['service'],
                        'risk_level': p['risk_level']
                    } for p in device.get('ports', [])]
                }
                devices.append(filtered_device)
            
            return jsonify({
                'devices': devices,
                'total': len(self.network_monitor.known_devices)
            })

        @app.route('/api/events')
        def get_events():
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 10))
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            
            return jsonify({
                'events': list(self.events)[start_idx:end_idx],
                'total': len(self.events)
            })

    def add_event(self, event_type: str, device_info: dict, risk_level: str = 'low'):
        """Add a new event to the events list."""
        event = {
            'type': event_type,
            'device': device_info,
            'risk_level': risk_level,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.events.appendleft(event)  # Add new events to the left (most recent)

    def run(self):
        """Start the web interface."""
        host = os.getenv('WEB_HOST', '127.0.0.1')
        port = int(os.getenv('WEB_PORT', 5000))
        debug = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        app.run(host=host, port=port, debug=debug)