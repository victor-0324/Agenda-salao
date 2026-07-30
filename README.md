# Kryptacode

SaaS de agendamento automático para salões de beleza e barbearias, feito em Flask. Multi-tenant: cada salão tem sua própria conta, seus próprios serviços, clientes e link público de agendamento.

## O que tem pronto

- **Landing page de vendas** (`/`) e **página de preços** (`/precos`) com 3 planos (Starter, Pro, Premium)
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
