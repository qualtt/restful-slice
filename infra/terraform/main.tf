terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.66.1"
    }
  }
}

provider "proxmox" {
  # Замени IP на адрес твоего Proxmox
  endpoint  = var.proxmox_endpoint

  # То, что мы получили в ШАГЕ 2
  api_token = var.proxmox_api_token
  insecure  = true
}

variable "proxmox_endpoint" {
  type    = string
  default = "https://192.168.195.133:8006/"
}

variable "proxmox_api_token" {
  type      = string
  sensitive = true
}

# Переменная для твоего SSH ключа (замени на свой pub-ключ из Шага 3)
variable "ssh_key" {
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKbuSa136XxQkpeB5DNynJ4a6HfujTNjQW7GAgExcbAe admin@restful-slice-admin"
}

# --- ВМ 1: Менеджер (Мозг) ---
resource "proxmox_virtual_environment_vm" "proxmox-manager" {
  name        = "proxmox-manager"
  node_name   = "pve" # Имя твоей ноды Proxmox (обычно pve)
  vm_id       = 101

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores = 4
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = 6144 # 6 GB
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = "local-lvm:vm-9000-disk-0"
    interface    = "scsi0"
    size         = 30 # Увеличиваем диск до 30 ГБ
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp" # Роутер сам выдаст IP. Потом мы свяжем их через Tailscale
      }
    }
    user_account {
      username = "debian" # Дефолтный юзер
      keys     = [var.ssh_key]
    }
  }
}

# --- ВМ 2: Воркер 1 ---
resource "proxmox_virtual_environment_vm" "proxmox-worker-1" {
  name        = "proxmox-worker-1"
  node_name   = "pve"
  vm_id       = 102

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores = 5
  }

  memory {
    dedicated = 5120 # 5 GB
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = "local-lvm:vm-9000-disk-0"
    interface    = "scsi0"
    size         = 25
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
    user_account {
      username = "debian"
      keys     = [var.ssh_key]
    }
  }
}

# --- ВМ 3: Воркер 2 ---
resource "proxmox_virtual_environment_vm" "proxmox-worker-2" {
  name        = "proxmox-worker-2"
  node_name   = "pve"
  vm_id       = 103

  clone {
    vm_id = 9000
    full  = true
  }

  cpu {
    cores = 5
  }

  memory {
    dedicated = 5120 # 5 GB
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = "local-lvm:vm-9000-disk-0"
    interface    = "scsi0"
    size         = 25
  }

  network_device {
    bridge = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
    user_account {
      username = "debian"
      keys     = [var.ssh_key]
    }
  }
}

# Выводим IP адреса после создания
output "vm_ips" {
  value = {
    manager  = proxmox_virtual_environment_vm.proxmox-manager.ipv4_addresses
    worker-1 = proxmox_virtual_environment_vm.proxmox-worker-1.ipv4_addresses
    worker-2 = proxmox_virtual_environment_vm.proxmox-worker-2.ipv4_addresses
  }
}
