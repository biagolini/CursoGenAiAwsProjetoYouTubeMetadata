# Propósito

Aplica os metadados gerados pelo AWS Bedrock aos vídeos do YouTube, atualizando títulos, descrições, tags, localizações e configurações de agendamento automaticamente.

# O que o código faz

1. **Carrega** metadados do arquivo JSON gerado pelo script 07
2. **Autentica** com a YouTube Data API usando OAuth 2.0 (reutiliza token válido)
3. **Processa cada vídeo** individualmente:
   - Busca dados atuais do vídeo
   - Aplica novos metadados (título, descrição, tags)
   - Atualiza localizações em múltiplos idiomas
   - Configura agendamento de publicação (se data for futura)
4. **Relatório** detalhado do progresso e resultados

# Funcionalidades

### Metadados Aplicados
- **Título**: No idioma padrão configurado
- **Descrição**: Com referências e links adicionais
- **Tags**: Extraídos dos metadados gerados
- **Categoria**: Education (ID: 27)
- **Idioma padrão**: Configurável via `YOUTUBE_DEFAULT_LANGUAGE`

### Localizações Multilíngues
Aplica título e descrição em todos os idiomas disponíveis nos metadados (exceto o idioma padrão):
- Português (pt)
- Inglês (en)
- Espanhol (es)

### Configurações de Publicação
- **Status**: Privado (para vídeos agendados)
- **Agendamento**: Data/hora futura configurada
- **COPPA**: Não direcionado para crianças
- **Validação**: Verifica se data é futura antes de agendar

### Autenticação Inteligente
- **Reutilização**: Usa token existente se válido
- **Renovação automática**: Gera novo token apenas quando necessário
- **Transparência**: Informa quando renova credenciais
- **Eficiência**: Evita autenticação desnecessária

# Saída do script

```
=== Aplicação de Metadados no YouTube ===

Metadados carregados: 4 vídeos

Configurando cliente YouTube...
[OK] Cliente configurado

[1/4] Processando vídeo: 1qsgjjl3SaI
Atualizando vídeo: 1qsgjjl3SaI
  Vídeo encontrado
  Usando idioma configurado: pt
  Título: Amazon Q Developer Overview: Getting Started...
  Localizações: 2 idiomas
  Agendado para: 2025-11-15T16:30:00Z
  Vídeo atualizado com sucesso

=== Processamento Concluído ===
Vídeos atualizados com sucesso: 4/4
[OK] Todos os vídeos foram atualizados!
```

# Validações e Segurança

### Verificações Automáticas
- **Existência do vídeo**: Confirma que o vídeo existe no canal
- **Data futura**: Valida agendamento apenas para datas futuras
- **Formato de data**: Verifica formato ISO 8601
- **Permissões**: Usa escopo `youtube.force-ssl` para atualizações completas

### Tratamento de Erros
- **Vídeo não encontrado**: Continua com próximo vídeo
- **Erro de API**: Log detalhado e continua processamento
- **Data inválida**: Ignora agendamento mas aplica outros metadados
- **Falha de autenticação**: Para execução com erro claro

# Pré-requisitos

### Arquivo de Metadados
- Execute `07_metadata_generator.py` primeiro
- Arquivo configurado em `METADATA_OUTPUT_FILE` deve existir
- Metadados devem estar no formato correto

### Credenciais YouTube
- Arquivo `client_secret.json` configurado (OAuth 2.0)
- Token será gerado/reutilizado automaticamente em `token_admin.json`
- Escopo: `https://www.googleapis.com/auth/youtube.force-ssl`

### Dependências Python
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

# Configuração

## Variáveis do .env
- `METADATA_OUTPUT_FILE`: Localização dos metadados gerados
- `YOUTUBE_DEFAULT_LANGUAGE`: Idioma padrão (pt, en, es)

## Constantes do Código
- **SCOPES**: Permissões YouTube (force-ssl)
- **Categoria padrão**: Education (ID: 27)

# Como usar

1. **Certifique-se** que os metadados foram gerados:
   ```bash
   python 07_metadata_generator.py
   ```

2. **Execute o script**:
   ```bash
   python 08_update_youtube.py
   ```

3. **Autentique** quando solicitado (apenas se necessário)

4. **Monitore** o progresso no terminal

5. **Verifique** os vídeos no YouTube Studio

# Características Técnicas

### Processamento Individual
- **Isolado**: Cada vídeo é processado independentemente
- **Resiliente**: Falha em um vídeo não afeta os outros
- **Detalhado**: Log específico para cada operação
- **Incremental**: Pode ser executado múltiplas vezes

### Estrutura de Dados
- **Input**: JSON com video_id como chave
- **Validação**: Verifica estrutura antes de aplicar
- **Flexível**: Aplica apenas campos disponíveis
- **Compatível**: Formato padrão YouTube Data API

### Gerenciamento de Token
- **Inteligente**: Só autentica quando necessário
- **Persistente**: Salva token para reutilização
- **Robusto**: Trata expiração automaticamente
- **Transparente**: Informa status da autenticação

# Limitações

- **Rate Limits**: YouTube API tem limites de quota
- **Vídeos privados**: Apenas o proprietário pode atualizar
- **Agendamento**: Requer data futura e status privado
- **Localizações**: Limitado aos idiomas nos metadados gerados

# Próximos passos

Após executar este script:
1. Verifique os vídeos no YouTube Studio
2. Confirme agendamentos de publicação
3. Teste visualizações em diferentes idiomas
4. Monitore performance dos metadados otimizados
