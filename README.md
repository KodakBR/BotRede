# Bot de Monitoramento de Rede

Um bot de monitoramento de rede que detecta dispositivos na sua rede e envia notificações através do Discord.

## Recursos

- Descoberta de dispositivos na rede
- Varredura de portas
- Notificações via Discord
- Interface web para monitoramento
- Avaliação de nível de risco
- Detecção em tempo real de mudanças na rede

## Pré-requisitos

- Python 3.7 ou superior
- Nmap (Network Mapper)

## Instalação

### 1. Instalar o Python

Certifique-se de ter o Python 3.7 ou superior instalado. Você pode baixá-lo em [python.org](https://www.python.org/downloads/).

### 2. Instalar o Nmap

#### Windows
1. Baixe o instalador do Nmap em [nmap.org](https://nmap.org/download.html#windows)
2. Execute o instalador
3. Adicione o Nmap ao PATH do seu sistema, se não for feito automaticamente durante a instalação

#### Linux
Instale o Nmap utilizando o gerenciador de pacotes da sua distribuição:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install nmap
```

**Fedora:**
```bash
sudo dnf install nmap
```

**Arch Linux:**
```bash
sudo pacman -S nmap
```

### 3. Configurar o projeto

1. Clone o repositório ou faça o download do código-fonte
2. Crie um ambiente virtual:
   ```bash
   python -m venv venv
   ```

3. Ative o ambiente virtual:

   **Windows:**
   ```bash
   .\venv\Scripts\activate
   ```

   **Linux:**
   ```bash
   source venv/bin/activate
   ```

4. Instale as dependências:
   ```bash
   python setup.py install
   ```

### 4. Configurar o bot

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
DISCORD_TOKEN=seu_token_do_bot_discord
DISCORD_USER_ID=seu_id_de_usuario_no_discord
SCAN_INTERVAL=300
PORT_SCAN_TIMEOUT=2
PORT_SCAN_COMMON=True
```

## Uso

1. Certifique-se de que seu ambiente virtual esteja ativado
2. Execute o bot:
   ```bash
   python main.py
   ```

## Comandos do Discord

- `/clear` - Limpa as mensagens do bot na sua DM

## Considerações de Segurança

- O bot requer privilégios de administrador/root para realizar a varredura de rede
- Certifique-se de manter seu token do bot do Discord seguro
- Revise as configurações de varredura de portas para cumprir as políticas da sua rede

## Solução de Problemas

1. Se o Nmap não for encontrado:
   - Verifique se o Nmap está instalado corretamente
   - Certifique-se de que o Nmap esteja no PATH do seu sistema
   - Tente executar `nmap -V` no terminal ou prompt de comando

2. Se as notificações do Discord não estiverem funcionando:
   - Verifique o token do bot e o ID do usuário no arquivo `.env`
   - Certifique-se de que o bot possua as permissões adequadas
   - Verifique se as configurações de privacidade do Discord permitem DMs do bot

## Licença

Este projeto está licenciado sob a Licença MIT - consulte o arquivo LICENSE para mais detalhes.

