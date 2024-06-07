import paramiko
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, ProgressColumn, BarColumn, TextColumn
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
import time
import os
import signal
import sys
import configparser


def signal_handler(sig, frame):
    os.system('cls' if os.name == 'nt' else 'clear')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class UsageColumn(ProgressColumn):
    def render(self, task):
        """Show used/total."""
        return Text(f"{task.completed}/{task.total}", style="progress.percentage")

config = configparser.ConfigParser()
config.read('config.ini')

hostname = config.get('SSH', 'hostname')
port = config.getint('SSH', 'port')
username = config.get('SSH', 'username')
password = config.get('SSH', 'password')

def get_vps_stats(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command("free -m")
    ram_usage = stdout.read().decode().splitlines()[1].split()
    ram_total = int(ram_usage[1])
    ram_used = int(ram_usage[2])
    
    stdin, stdout, stderr = ssh_client.exec_command("uptime -p")
    uptime = stdout.read().decode().strip()
    
    stdin, stdout, stderr = ssh_client.exec_command("df -h --total | grep total")
    storage = stdout.read().decode().split()
    storage_total = storage[1]
    storage_used = storage[2]
    
    stdin, stdout, stderr = ssh_client.exec_command("top -bn1 | grep '%Cpu(s)'")
    cpu = stdout.read().decode().split()
    cpu_usage = float(cpu[1].strip('%us,'))

    stdin, stdout, stderr = ssh_client.exec_command('systemctl is-active boxy-ben')
    boxy_ben_status = stdout.read().decode().strip()

    stdin, stdout, stderr = ssh_client.exec_command('systemctl is-active boxy-flo')
    boxy_flo_status = stdout.read().decode().strip()

    stdin, stdout, stderr = ssh_client.exec_command('systemctl is-active minecraftserver')
    minecraftserver_status = stdout.read().decode().strip()

    stdin, stdout, stderr = ssh_client.exec_command('lsb_release -d')
    distro_name = stdout.read().decode().split(":")[1].strip()
    stdin, stdout, stderr = ssh_client.exec_command('uname -r')
    kernel_version = stdout.read().decode().strip()

    return {
        'ram_total': ram_total,
        'ram_used': ram_used,
        'uptime': uptime,
        'storage_total': storage_total,
        'storage_used': storage_used,
        'cpu_usage': cpu_usage,
        'boxy_ben_status': boxy_ben_status,
        'boxy_flo_status': boxy_flo_status,
        'minecraftserver_status': minecraftserver_status,
        'distro_name': distro_name,
        'kernel_version': kernel_version
    }

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to the VPS...")
ssh_client.connect(hostname, port, username, password)

console = Console()

def display_stats():
    with Live(console=console, refresh_per_second=2):
        while True:
            try:
                stats = get_vps_stats(ssh_client)
                os.system('cls' if os.name == 'nt' else 'clear')

                terminal_width = os.get_terminal_size().columns

                bar_column = BarColumn(terminal_width) 
                text_column = TextColumn("[bold blue]{task.description}", justify="left")

                with Progress(text_column, bar_column, UsageColumn(), expand=False) as progress: 
                    ram_task = progress.add_task("[cyan]RAM Usage", total=stats['ram_total'], completed=stats['ram_used'])
                    storage_task = progress.add_task("[cyan]Storage Usage", total=float(stats['storage_total'].rstrip('G')), completed=float(stats['storage_used'].rstrip('G')))
                    cpu_task = progress.add_task("[cyan]CPU Usage", total=100, completed=stats['cpu_usage'])

                table = Table(show_header=True, header_style="bold magenta", width=terminal_width, style="cyan")
                table.add_column("Service", justify="left", width=terminal_width - 9)  
                table.add_column("Status", justify="right", width=10)

                table.add_row("boxy-ben", "[green]" + stats['boxy_ben_status'] + "[/green]" if stats['boxy_ben_status'] == 'active' else "[red]" + stats['boxy_ben_status'] + "[/red]")
                table.add_row("boxy-flo", "[green]" + stats['boxy_flo_status'] + "[/green]" if stats['boxy_flo_status'] == 'active' else "[red]" + stats['boxy_flo_status'] + "[/red]")
                table.add_row("minecraftserver", "[green]" + stats['minecraftserver_status'] + "[/green]" if stats['minecraftserver_status'] == 'active' else "[red]" + stats['minecraftserver_status'] + "[/red]")

                console.print(table)

                distro_kernel_info = f"[purple]Distro:[/purple] [cyan]{stats['distro_name']}[/cyan], [purple]Kernel:[/purple] [cyan]{stats['kernel_version']}[/cyan]"
                uptime_info = f"[purple]Uptime:[/purple] [cyan]{stats['uptime']}[/cyan]"
                panel_content = f"{distro_kernel_info}, {uptime_info:>}"
                panel = Panel(panel_content, width=terminal_width, expand=True)
                console.print(panel)
                time.sleep(2)
            except KeyboardInterrupt:
                print("Program interrupted")
                break

display_stats()
