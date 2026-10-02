# SalonPro

SaaS de agendamento automático para salões de beleza e barbearias, feito em Flask. Multi-tenant: cada salão tem sua própria conta, seus próprios serviços, clientes e link público de agendamento.

## O que tem pronto

- **Landing page de vendas** (`/`) e **página de preços** (`/precos`) com 3 planos (premium, Pro, Premium)
- **Cadastro de salão** (`/conta/cadastro`) — cria o salão (tenant) e o usuário dono
- **Login/logout** (`/conta/login`)
- **Painel do salão** (`/painel`), protegido por login, sempre filtrado pelo `salon_id` do usuário logado:
  - Visão geral com agenda do dia e uso do plano
  - Serviços (CRUD, com limite por plano)
  - Clientes (CRUD)
  - Agendamentos por dia, com confirmar/concluir/cancelar
  - Configurações: dados do salão e horário de funcionamento por dia da semana
- **Página pública de agendamento** (`/agendar/<slug-do-salao>`):
  - Mostra o perfil do salão: foto, endereço/localização e links de Instagram e WhatsApp
  - Cliente escolhe o serviço, o dia e um horário realmente livre (calculado a partir do horário de funcionamento menos os agendamentos já existentes)
  - Preenche nome/telefone e confirma — sem precisar criar conta
  - Cliente é criado/atualizado automaticamente no salão
- **Regra de negócio de planos**: cada plano tem limite de serviços e de agendamentos por mês, aplicado tanto no painel quanto na página pública

## Se você já tinha o projeto rodando (banco existente)

Esta versão adicionou colunas novas na tabela `salons` (`address`, `instagram`, `whatsapp`, `profile_photo`). Se seu banco já existia antes dessas colunas, rode a migração uma vez:

```bash
python migrate.py
```

Isso adiciona as colunas que faltam sem apagar nenhum dado. É seguro rodar mais de uma vez — se não houver nada a fazer, ele só avisa. Funciona tanto com SQLite quanto com MySQL.

Se preferir, também dá pra simplesmente apagar o banco e rodar `python seed.py` de novo para recomeçar com dados de demonstração.

## Fotos de perfil enviadas pelos salões

As fotos enviadas em Configurações ficam salvas em `UPLOAD_FOLDER` (variável de ambiente opcional no `.env`). Se não definir nada, elas vão para `app/static/uploads/` automaticamente. A página pública sempre serve as fotos pela rota `/agendar/midia/<arquivo>`, então funciona mesmo se você apontar `UPLOAD_FOLDER` para uma pasta fora de `static/`.

## Rodando localmente

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# opcional: cria um salão de demonstração já com serviços cadastrados
python seed.py

python run.py
```

Acesse `http://localhost:5000`.

Se rodar o `seed.py`, o login de teste é `demo@salao.com` / `123456`, e a página pública fica em `http://localhost:5000/agendar/studio-bella-hair`.

O banco é SQLite por padrão (`agendasalao.db`, criado automaticamente). Para produção, defina a variável de ambiente `DATABASE_URL` apontando para Postgres/MySQL e troque a `SECRET_KEY`.

## Estrutura

```
app/
  auth/         cadastro, login, logout
  main/         landing page e preços
  dashboard/    painel do salão (autenticado, multi-tenant)
  booking/      página pública de agendamento
  templates/    HTML de cada área
  static/css/   design system (cores, tipografia, componentes)
  models.py     Salon, User, Service, Client, Appointment
  config.py     planos, horários padrão, chave secreta
```

## Próximos passos sugeridos (não incluídos)

- Integração de pagamento real (Stripe/Mercado Pago) para cobrar os planos automaticamente
- Envio de e-mail/WhatsApp de confirmação e lembrete de horário
- Múltiplos profissionais com agenda individual (hoje o campo "profissional" existe no modelo mas não tem tela própria)
- Página de onboarding pós-cadastro guiando o dono a cadastrar o primeiro serviço

## Evolução multi-profissional (2026-09)

O sistema agora suporta múltiplos profissionais por salão, cada um com agenda semanal própria e serviços específicos.

### Novidades
- Cadastro de profissionais por salão.
- Horário semanal individual por profissional.
- Vínculo N:N entre profissionais e serviços.
- Agendamento público escolhe o profissional antes do horário.
- Conflitos de agenda são calculados por profissional, permitindo atendimentos simultâneos no mesmo salão.
- Filtro da agenda do painel por profissional.
- Planos Essencial, Pro e Premium com limites progressivos de profissionais, serviços e agendamentos.

### Atualizando um banco existente

Antes de subir a nova versão em produção, faça backup do banco e rode:

```bash
python migrate.py
```

A migração é idempotente e cria automaticamente um profissional padrão para cada salão antigo, vinculando os serviços existentes para manter os links de agendamento funcionando.

### Próxima camada recomendada

A estrutura já está preparada para evoluir com login individual do profissional, comissão por serviço, bloqueios/folgas por data, férias, recorrência, múltiplas unidades e relatórios financeiros por profissional.

## Planos comerciais (v3)

| Plano | Preço | Estabelecimentos | Serviços | Profissionais | Recursos |
|---|---:|---:|---|---|---|
| Basic | R$ 29,90/mês | 1 | Até 10 | proprietário padrão; não adiciona equipe | agenda e gestão básica |
| Premium | R$ 59,90/mês | 1 | Ilimitados | até 5 | área financeira e relatórios CSV |
| Pro | R$ 99,90/mês | 1 | Ilimitados | mais de 5 | área do cliente, avaliações e financeiro |

### Área do cliente (Pro)
O cliente ativa o acesso usando o mesmo telefone cadastrado no agendamento e cria uma senha. Depois pode consultar seus horários, remarcar ou cancelar atendimentos futuros e avaliar atendimentos concluídos.

### Avaliações (Pro)
Cada agendamento concluído pode receber uma única avaliação de 1 a 5 estrelas, vinculada ao cliente e ao profissional. O painel Pro exibe média geral, média por profissional e comentários recentes.

### Financeiro (Premium e Pro)
Cada agendamento pode ser marcado como pago ou pendente, com valor recebido e forma de pagamento. O painel exibe recebido, a receber, totais por forma de pagamento e permite exportar relatório mensal em CSV.

### Atualizando uma instalação existente
Faça backup do banco e execute:

```bash
python migrate.py
```

A migração cria os novos campos sem apagar dados e converte os planos da versão anterior: `essencial -> basic`, `pro antigo -> premium` e `premium antigo -> pro`.
