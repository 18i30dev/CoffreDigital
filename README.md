# Coffre Digital

Um gerenciador de senhas simples e local, feito em Python com interface grafica. Tudo fica no seu computador — nada vai para a nuvem.

## O que ele faz

- Guarda senhas de sites e serviços em um banco local (`cofre.db`).
- Criptografa as senhas antes de gravar no disco.
- Pede uma senha mestre para abrir o cofre.
- Deixa adicionar, copiar, excluir e gerar senhas aleatórias.
- Funciona completamente offline.

## Como instalar (Windows)

### Jeito mais fácil: executavel pronto
1. Abra a pasta `dist/` dentro dessa mesma pasta.
2. Dê um duplo clique em `CoffreDigital.exe`.
3. Não precisa instalar nada. O programa abre direto na tela de login, sem aquela janela preta de terminal.

### Como o programa se comporta
- So da para ter uma sessao aberta por vez. Se tentar abrir novamente enquanto ja estiver rodando, ele restaura a janela existente em vez de abrir outra copia.
- Clicando no **X**, o programa some da tela e vai para a bandeja do sistema (aqueles icones escondidos perto do relogio). Clique com o botao direito no icone do cadeado para **Mostrar Coffre** ou **Sair**.
- O botao **Sair** dentro da janela fecha o programa de verdade e deixa livre para abrir de novo.

### Recuperacao da senha mestre
Na primeira vez que voce cria a senha mestre, o programa mostra uma **Chave de Recuperacao** (tipo `a3f7b2...`). **Anote essa chave em papel e guarde em lugar seguro.** Sem ela, se voce esquecer a senha mestre, nao tem como recuperar nada.

Esse arquivo `recovery.key` fica salvo na pasta do programa e permite redefinir a senha mestre totalmente offline. Se esquecer a senha mestre, clique em **“Esqueci a senha mestre”** na tela de login, digite a Chave de Recuperacao e defina uma nova. Todas as suas senhas salvas serao recriptografadas com a nova senha mestre.

Ja logado, clique em **“Ver Chave Recuperacao”** na janela principal para ver a chave novamente.

**Aviso importante:** se voce perder a senha mestre E a Chave de Recuperacao, suas senhas ficam inacessiveis para sempre. Isso e proposital — por seguranca, ninguem (nem voce) consegue acessar sem elas.

### Se quiser mexer no codigo (via Python)
1. Dê um duplo clique em `instalar.bat`.
2. Aguarde a instalacao das dependências.
3. Execute `cofre.pyw`.

## Como usar

1. Na primeira execução, crie sua senha mestre. Ela é a chave do seu cofre.
2. Nas execuções seguintes, digite a mesma senha mestre para entrar.
3. Use **“+ Adicionar”** para cadastrar um serviço.
4. Use **“Copiar”** para colar a senha em outro lugar.
5. Use **“Gerar Senha”** para criar uma senha forte aleatória.

## Sobre segurança

Este projeto é educacional e de portifólio. Ele protege contra quem pegar o arquivo e tentar ler de repente, mas não substitui gerenciadores profissionais como Bitwarden ou 1Password.

Não perca sua senha mestre: sem ela, não há como recuperar as senhas salvas.

## No GitHub

Se for colocar esse projeto no GitHub, **não commite esses arquivos**:

- `cofre.db` — o banco com suas senhas
- `recovery.key` e `recovery_view.key` — suas chaves de recuperação
- `backup_senhas.txt` — backup com senhas em texto puro
- `cofre.salt` — o salt de criptografia
- `dist/`, `build/`, `__pycache__/` — arquivos gerados na compilação

Um `.gitignore` ja está incluido na pasta para ajudar a nao subir isso por acidente.