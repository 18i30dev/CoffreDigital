import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import sqlite3
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import string
import random

# ----------------------------
# Configuracao visual
# ----------------------------
ctk.set_appearance_mode("dark")   # Tema escuro
ctk.set_default_color_theme("blue")


class BancoSenhas:
    """Gerencia o arquivo local (SQLite) e a criptografia das senhas."""

    def __init__(self, arquivo="cofre.db", chave_mestre=""):
        self.arquivo = arquivo
        self.chave_mestre = chave_mestre
        self.fernet = None          # Objeto que criptografa e descriptografa
        self.conexao = None         # Conexao com o banco SQLite

        if chave_mestre:
            self._inicializar_criptografia()
            self._conectar()
            self._criar_tabela()

    def _inicializar_criptografia(self):
        """Transforma a senha mestre em uma chave de criptografia Fernet."""
        salt = b'cofre_salt_fixo_123'  # Em um projeto real, esse sal seria unico e salvo separado
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000
        )
        chave = base64.urlsafe_b64encode(kdf.derive(self.chave_mestre.encode()))
        self.fernet = Fernet(chave)

    def _conectar(self):
        self.conexao = sqlite3.connect(self.arquivo)

    def _criar_tabela(self):
        """Cria a tabela se ainda nao existir e garante coluna de exclusao."""
        cursor = self.conexao.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS senhas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servico TEXT NOT NULL,
                usuario TEXT,
                senha_criptografada TEXT NOT NULL,
                excluido INTEGER DEFAULT 0
            )
        """)
        # Se a tabela ja existia sem a coluna excluido, tenta adicionar
        try:
            cursor.execute("ALTER TABLE senhas ADD COLUMN excluido INTEGER DEFAULT 0")
        except Exception:
            # Coluna ja existe ou outro erro ignoravel
            pass
        self.conexao.commit()

    def adicionar(self, servico, usuario, senha):
        """Salva uma senha criptografada no banco."""
        senha_cript = self.fernet.encrypt(senha.encode()).decode()
        cursor = self.conexao.cursor()
        cursor.execute(
            "INSERT INTO senhas (servico, usuario, senha_criptografada) VALUES (?, ?, ?)",
            (servico, usuario, senha_cript)
        )
        self.conexao.commit()

    def listar_todas(self):
        """Retorna todas as senhas, incluindo as marcadas como excluida."""
        cursor = self.conexao.cursor()
        cursor.execute("SELECT id, servico, usuario, senha_criptografada, excluido FROM senhas")
        linhas = cursor.fetchall()
        resultado = []
        for linha in linhas:
            id_, servico, usuario, senha_cript, excluido = linha
            senha = self.fernet.decrypt(senha_cript.encode()).decode()
            resultado.append((id_, servico, usuario, senha, bool(excluido)))
        return resultado

    def listar(self):
        """Retorna apenas as senhas nao excluidas (para exibir na lista principal)."""
        cursor = self.conexao.cursor()
        cursor.execute("SELECT id, servico, usuario, senha_criptografada FROM senhas WHERE excluido = 0")
        linhas = cursor.fetchall()
        resultado = []
        for linha in linhas:
            id_, servico, usuario, senha_cript = linha
            senha = self.fernet.decrypt(senha_cript.encode()).decode()
            resultado.append((id_, servico, usuario, senha))
        return resultado

    def excluir(self, id_):
        """Marca a entrada como excluida (soft delete) sem apagar do banco."""
        cursor = self.conexao.cursor()
        cursor.execute("UPDATE senhas SET excluido = 1 WHERE id=?", (id_,))
        self.conexao.commit()

    def fazer_backup_texto(self):
        """Exporta todas as senhas descriptografadas para um arquivo de texto na pasta do programa."""
        senhas = self.listar_todas()
        with open("backup_senhas.txt", "w", encoding="utf-8") as f:
            f.write("=== BACKUP DO COFRE DIGITAL ===\n")
            f.write("Gerado automaticamente ao salvar senhas.\n")
            f.write("ATENCAO: este arquivo contem senhas em texto puro. Nao compartilhe.\n\n")
            for id_, servico, usuario, senha, excluida in senhas:
                status = " (EXCLUIDA)" if excluida else ""
                f.write(f"Servico: {servico}{status}\n")
                f.write(f"Usuario: {usuario if usuario else '-'}\n")
                f.write(f"Senha: {senha}\n")
                f.write("-" * 30 + "\n")


class TelaLogin(ctk.CTk):
    """Primeira janela: pede a senha mestre para desbloquear o cofre."""

    def __init__(self):
        super().__init__()
        self.title("Coffre Digital - Login")
        self.geometry("400x250")
        self.resizable(False, False)

        self.label = ctk.CTkLabel(self, text="Digite sua senha mestre:", font=("Arial", 14))
        self.label.pack(pady=30)

        self.entrada = ctk.CTkEntry(self, show="*", width=250)
        self.entrada.pack(pady=10)
        self.entrada.bind("<Return>", lambda event: self.tentar_login())

        self.botao = ctk.CTkButton(self, text="Entrar", command=self.tentar_login)
        self.botao.pack(pady=20)

        self.senha_correta = None

    def tentar_login(self):
        senha = self.entrada.get()
        if not senha:
            messagebox.showwarning("Atencao", "Digite uma senha.")
            return

        # Primeira vez: cria o banco com essa senha mestre
        if not os.path.exists("cofre.db"):
            self.senha_correta = senha
            self.destroy()
        else:
            # Tenta abrir o banco com essa senha; se falhar, a senha esta errada
            try:
                banco = BancoSenhas("cofre.db", senha)
                # Se chegou aqui, a senha esta certa
                self.senha_correta = senha
                self.destroy()
            except Exception:
                messagebox.showerror("Erro", "Senha mestre incorreta.")


class AppCofre(ctk.CTk):
    """Janela principal: lista, adiciona, exclui e gera senhas."""

    def __init__(self, chave_mestre):
        super().__init__()
        self.title("Coffre Digital - Minhas Senhas")
        self.geometry("700x500")

        self.banco = BancoSenhas("cofre.db", chave_mestre)

        # Titulo
        self.titulo = ctk.CTkLabel(self, text="Meu Cofre de Senhas", font=("Arial", 20, "bold"))
        self.titulo.pack(pady=15)

        # Lista de senhas
        self.frame_lista = ctk.CTkScrollableFrame(self, width=650, height=280)
        self.frame_lista.pack(pady=10)

        # Botoes abaixo da lista
        self.frame_botoes = ctk.CTkFrame(self)
        self.frame_botoes.pack(pady=10)

        self.btn_adicionar = ctk.CTkButton(
            self.frame_botoes, text="+ Adicionar", command=self.adicionar_senha, width=140
        )
        self.btn_adicionar.grid(row=0, column=0, padx=10)

        self.btn_gerar = ctk.CTkButton(
            self.frame_botoes, text="Gerar Senha", command=self.gerar_senha, width=140
        )
        self.btn_gerar.grid(row=0, column=1, padx=10)

        self.btn_reset = ctk.CTkButton(
            self.frame_botoes, text="Reset Total", command=self.reset_total, width=140, fg_color="red", hover_color="darkred", state="disabled"
        )
        self.btn_reset.grid(row=0, column=2, padx=10)

        self.btn_sair = ctk.CTkButton(
            self.frame_botoes, text="Sair", command=self.quit, width=100, fg_color="gray40"
        )
        self.btn_sair.grid(row=0, column=3, padx=10)

        self.carregar_lista()

    def carregar_lista(self):
        """Limpa e reexibe todas as senhas salvas."""
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        try:
            senhas = self.banco.listar()
        except Exception as e:
            messagebox.showerror("Erro", f"Nao foi possivel carregar: {e}")
            return

        if not senhas:
            vazio = ctk.CTkLabel(self.frame_lista, text="Nenhuma senha salva ainda.")
            vazio.pack(pady=20)
            self.btn_reset.configure(state="disabled")
            return

        self.btn_reset.configure(state="normal")

        for id_, servico, usuario, senha in senhas:
            linha = ctk.CTkFrame(self.frame_lista)
            linha.pack(fill="x", pady=5, padx=10)

            texto = f"{servico} | {usuario if usuario else '-'}"
            lbl = ctk.CTkLabel(linha, text=texto, anchor="w", width=300)
            lbl.pack(side="left", padx=10)

            btn_copiar = ctk.CTkButton(
                linha, text="Copiar", width=80,
                command=lambda s=senha: self.copiar(s)
            )
            btn_copiar.pack(side="right", padx=5)

            btn_apagar = ctk.CTkButton(
                linha, text="Excluir", width=80, fg_color="red", hover_color="darkred",
                command=lambda i=id_: self.excluir(i)
            )
            btn_apagar.pack(side="right", padx=5)

    def adicionar_senha(self):
        """Abre caixas de dialogo para cadastrar uma nova senha."""
        servico = simpledialog.askstring("Novo cadastro", "Servico (ex: Gmail, Netflix):")
        if not servico:
            return
        usuario = simpledialog.askstring("Novo cadastro", "Usuario / e-mail (opcional):") or ""
        senha = simpledialog.askstring("Novo cadastro", "Senha:", show="*")
        if not senha:
            return

        try:
            self.banco.adicionar(servico, usuario, senha)
            self.banco.fazer_backup_texto()
            self.carregar_lista()
            messagebox.showinfo("Sucesso", "Senha salva com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Nao foi possivel salvar: {e}")

    def gerar_senha(self):
        """Gera uma senha aleatoria e salva no cofre com servico e usuario informados."""
        servico = simpledialog.askstring("Gerar senha", "Servico (ex: Gmail, Netflix):")
        if not servico:
            return
        usuario = simpledialog.askstring("Gerar senha", "Usuario / e-mail (opcional):") or ""

        tamanho = 12
        caracteres = string.ascii_letters + string.digits + "!@#$%&*"
        senha = ''.join(random.choice(caracteres) for _ in range(tamanho))

        try:
            self.banco.adicionar(servico, usuario, senha)
            self.banco.fazer_backup_texto()
            self.carregar_lista()
            self.clipboard_clear()
            self.clipboard_append(senha)
            messagebox.showinfo("Senha gerada", f"Senha gerada para {servico}:\n{senha}\n\nEla foi copiada para a area de transferencia e salva no cofre.")
        except Exception as e:
            messagebox.showerror("Erro", f"Nao foi possivel salvar: {e}")

    def copiar(self, senha):
        """Copia a senha para a area de transferencia."""
        self.clipboard_clear()
        self.clipboard_append(senha)
        messagebox.showinfo("Copiado", "Senha copiada para a area de transferencia.")

    def excluir(self, id_):
        """Confirma e exclui uma senha."""
        confirmar = messagebox.askyesno("Excluir", "Tem certeza que deseja apagar esta senha?")
        if confirmar:
            try:
                self.banco.excluir(id_)
                self.carregar_lista()
                messagebox.showinfo("Sucesso", "Senha excluida.")
            except Exception as e:
                messagebox.showerror("Erro", f"Nao foi possivel excluir: {e}")

    def reset_total(self):
        """Apaga todas as senhas apos confirmacao e validacao da senha mestre."""
        confirmar = messagebox.askyesno(
            "Reset Total",
            "TEM CERTEZA? Isso apaga TODAS as senhas do cofre de forma irreversível."
        )
        if not confirmar:
            return

        senha = simpledialog.askstring("Reset Total", "Digite sua senha mestre para confirmar:", show="*")
        if not senha:
            return

        # Valida se a senha digitada consegue abrir o banco
        try:
            teste = BancoSenhas("cofre.db", senha)
            # Se chegou aqui, a senha está correta
        except Exception:
            messagebox.showerror("Erro", "Senha mestre incorreta. Cancelando reset.")
            return

        try:
            cursor = self.banco.conexao.cursor()
            # Exporta backup antes de apagar tudo
            self.banco.fazer_backup_texto()
            cursor.execute("DELETE FROM senhas")
            self.banco.conexao.commit()
            self.carregar_lista()
            messagebox.showinfo("Reset Total", "Todas as senhas foram apagadas. Um backup foi gerado em backup_senhas.txt antes do reset.")
        except Exception as e:
            messagebox.showerror("Erro", f"Nao foi possivel resetar: {e}")


# ----------------------------
# Ponto de entrada
# ----------------------------
if __name__ == "__main__":
    login = TelaLogin()
    login.mainloop()

    # Após fechar a tela de login, se tivermos senha mestre, abrimos o app principal
    if login.senha_correta:
        app = AppCofre(login.senha_correta)
        app.mainloop()