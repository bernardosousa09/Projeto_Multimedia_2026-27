"""THE BLACKWOOD FILES — aplicação Web escolar em Python, HTML e CSS.

Não precisa de Flask, PyScript, JavaScript, bibliotecas nem Internet.
A lógica de TODOS os jogos é executada no servidor Python (biblioteca padrão).

Para iniciar: python3 app.py
O programa abre automaticamente http://127.0.0.1:8765 no navegador.
"""
from __future__ import annotations

import html
import os
import random
import re
import secrets
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse, quote

# %% [markdown]
# # PARTE 1 — HISTÓRIAS, PERSONAGENS E PERGUNTAS
# Conteúdo do antigo game_data.py. Casos do Detetive X e perguntas da Sala de Interrogatório.
# %%

def make_case(code, title, genre, intro, suspects, locations, primary, secondary,
              confrontations, culprit, motive, other_motives, valid_pairs,
              conclusion):
    evidence = {}
    for idx, item in enumerate(primary, 1):
        evidence[f"P{idx}"] = dict(zip(("location", "object", "title", "text"), item))
        evidence[f"P{idx}"]["kind"] = "principal"
    for idx, item in enumerate(secondary, 1):
        evidence[f"S{idx}"] = dict(zip(("location", "object", "title", "text"), item))
        evidence[f"S{idx}"]["kind"] = "secundária"
    return {
        "id": code, "title": title, "genre": genre, "intro": intro,
        "suspects": suspects, "locations": locations, "evidence": evidence,
        "confrontations": confrontations, "culprit": culprit,
        "motive": motive, "motive_options": [motive, *other_motives],
        "valid_pairs": valid_pairs, "conclusion": conclusion,
    }



# ## JOGO 1 — DETETIVE X: nove casos, suspeitos e provas
CASES = [
    make_case(
        "D1", "O Convite Misterioso", "Desaparecimento",
        "Alexander Blackwood desapareceu depois de receber um convite para uma reunião noturna. A última localização conhecida é a sede da empresa.",
        [("Daniel Mercer", "Sócio empresarial", "Alexander e eu tínhamos uma reunião de trabalho, mas não sei onde ele está."),
         ("Emma Collins", "Assistente", "Preparei a agenda da manhã seguinte. Não organizei nenhuma reunião noturna."),
         ("James Walker", "Chefe de segurança", "Vi movimentação no arquivo, mas não recebi nenhum alerta de emergência."),
         ("Oliver Blackwood", "Irmão", "Discutimos sobre negócios há dias. Ontem não nos encontrámos.")],
        ["Escritório", "Arquivo", "Sala de Segurança", "Garagem"],
        [("Escritório", "Email impresso", "Convite das 22h15", "Uma mensagem da conta de Daniel pede a Alexander que compareça no arquivo às 22h30."),
         ("Arquivo", "Leitor de cartões", "Acesso ao arquivo", "O cartão de Daniel abriu o arquivo às 22h38."),
         ("Arquivo", "Fechadura eletrónica", "Fecho da sala reservada", "O fecho da divisão foi ativado às 22h43 com a chave de segurança individual atribuída a Daniel."),
         ("Escritório", "Pasta financeira", "Transferências irregulares", "Alexander assinalou transferências autorizadas por Daniel e preparava um pedido de auditoria."),
         ("Sala de Segurança", "Monitor de vídeo", "Entrada acompanhada", "Uma gravação mostra Daniel a acompanhar Alexander até ao arquivo; Daniel regressa sozinho."),
         ("Garagem", "Registo do portão", "Saída de Daniel", "O veículo registado em nome de Daniel saiu às 22h49, após o fecho da sala reservada.")],
        [("Escritório", "Agenda de mesa", "Agenda de Alexander", "A reunião com o auditor estava marcada para a manhã seguinte."),
         ("Arquivo", "Caixa de documentos", "Inventário antigo", "Uma caixa de dossiers foi recentemente reorganizada, sem relação direta com o desaparecimento.")],
        [("Daniel Mercer", "P1", "Porque enviou este convite?", "Queria falar sobre números. Não imaginava que Alexander desaparecesse."),
         ("James Walker", "P5", "O que mostram estas imagens?", "Reconheço Daniel e Alexander. Vi Daniel regressar sozinho, mas pensei que fosse normal."),
         ("Daniel Mercer", "P3", "Porque utilizou a sua chave para fechar a divisão?", "Foi um procedimento de segurança... Não tenho mais nada a acrescentar.")],
        "Daniel Mercer", "Impedir a descoberta de irregularidades financeiras",
        ["Vender uma obra de arte", "Discutir a herança da família"],
        [("P3", "P5"), ("P1", "P3")],
        "Daniel enviou um falso convite, acompanhou Alexander ao arquivo e fechou-o numa divisão reservada para tentar ocultar transferências irregulares. Alexander é encontrado em segurança."
    ),
    make_case(
        "D2", "O Segredo de Família", "Desaparecimento",
        "Alexander desapareceu na véspera da reunião sobre a venda de uma propriedade da família Blackwood.",
        [("Oliver Blackwood", "Irmão", "Não concordo com a venda, mas nunca faria mal ao meu irmão."),
         ("Emma Collins", "Assistente", "A reunião da venda estava confirmada para amanhã."),
         ("James Walker", "Chefe de segurança", "A garagem esteve aberta para manutenção."),
         ("Sofia Bennett", "Curadora", "Saí da galeria antes da hora do desaparecimento.")],
        ["Escritório", "Garagem", "Sala de Segurança", "Galeria"],
        [("Escritório", "Correspondência", "Discussão da venda", "Mensagens de Oliver ameaçam impedir a venda da propriedade familiar."),
         ("Escritório", "Telemóvel", "Encontro marcado", "Oliver pediu a Alexander que fosse à garagem às 21h45, sem contar a ninguém."),
         ("Garagem", "Painel de acessos", "Chave da manutenção", "A sala de manutenção foi fechada às 21h51 com a chave pessoal de Oliver."),
         ("Sala de Segurança", "Gravação do portão", "Alexander na garagem", "A câmara mostra Alexander a entrar na garagem às 21h44."),
         ("Sala de Segurança", "Gravação de saída", "Oliver sai sozinho", "Às 21h54, Oliver sai da zona de manutenção sozinho; ninguém mais entrou nesse intervalo."),
         ("Escritório", "Contrato de venda", "Interesse no terreno", "O contrato confirma que Oliver perderia direitos de utilização do terreno após a venda.")],
        [("Galeria", "Livro de visitas", "Passagem pela galeria", "Sofia esteve na galeria nessa tarde."),
         ("Garagem", "Ferramentas", "Manutenção recente", "Foram reparadas prateleiras num compartimento diferente da sala fechada.")],
        [("Oliver Blackwood", "P2", "Porque chamou Alexander à garagem?", "Precisávamos de conversar longe dos advogados."),
         ("James Walker", "P3", "Quem tem essa chave?", "A chave registada é de Oliver. Não há indícios de cópia nesta investigação."),
         ("Oliver Blackwood", "P5", "Porque saiu sozinho?", "Ele disse que ficava mais algum tempo... Foi isso que aconteceu.")],
        "Oliver Blackwood", "Impedir a venda de uma propriedade familiar",
        ["Obter um contrato de manutenção", "Esconder um roubo de arte"],
        [("P2", "P3"), ("P3", "P5")],
        "Oliver atraiu Alexander à garagem e deixou-o trancado numa sala de manutenção para atrasar a venda. Alexander é libertado e a reunião pode ser retomada."
    ),
    make_case(
        "D3", "O Arquivo Proibido", "Desaparecimento",
        "Alexander desapareceu após anunciar que iria rever pessoalmente contratos confidenciais da empresa.",
        [("Emma Collins", "Assistente", "Imprimi os contratos, mas não sei o que aconteceu depois."),
         ("Lucas Reed", "Técnico informático", "Os sistemas estavam a funcionar normalmente."),
         ("James Walker", "Chefe de segurança", "Não recebi nenhum pedido de acesso especial."),
         ("Daniel Mercer", "Sócio", "Queria ver esses contratos, mas a reunião foi adiada.")],
        ["Escritório", "Arquivo", "Sala de Segurança", "Galeria"],
        [("Escritório", "Contratos", "Contratos alterados", "Os metadados das últimas alterações apontam para a conta de trabalho de Emma."),
         ("Escritório", "Bilhete na secretária", "Reunião inventada", "Uma nota pede a Alexander que procure os originais na sala reservada do arquivo."),
         ("Sala de Segurança", "Histórico da impressora", "Origem do bilhete", "O bilhete foi impresso às 20h31 no computador pessoal atribuído a Emma."),
         ("Arquivo", "Leitor de cartões", "Entrada de Emma", "O cartão de Emma abriu a zona reservada do arquivo às 20h39."),
         ("Arquivo", "Registo da fechadura", "Sala trancada", "O sistema regista que Emma fechou a sala reservada às 20h47 com a sua chave pessoal."),
         ("Sala de Segurança", "Áudio recuperado", "Mensagem de Alexander", "Alexander deixou uma mensagem a dizer que seguia o bilhete e que Emma lhe tinha indicado o local.")],
        [("Galeria", "Agenda de exposição", "Visita prevista", "Alexander tinha uma visita agendada à galeria para o dia seguinte."),
         ("Arquivo", "Etiquetas das caixas", "Caixas reorganizadas", "Algumas caixas mudaram de prateleira durante a semana.")],
        [("Emma Collins", "P1", "Porque alterou os contratos?", "Foram correções administrativas. Não achei necessário avisar Alexander."),
         ("James Walker", "P5", "Quem podia fechar aquela sala?", "O registo associa a operação à chave pessoal de Emma."),
         ("Emma Collins", "P3", "Porque imprimiu uma falsa reunião?", "Aquela nota era só um lembrete... Não pensei que fosse levada a sério.")],
        "Emma Collins", "Esconder alterações indevidas em contratos",
        ["Roubar uma pintura", "Adiar a venda de uma propriedade"],
        [("P3", "P5"), ("P2", "P5")],
        "Emma alterou contratos, atraiu Alexander ao arquivo e fechou-o na zona reservada para evitar que descobrisse as alterações. Alexander é encontrado."
    ),
    make_case(
        "R1", "A Pintura Falsa", "Roubo",
        "A pintura Nocturne, peça central da Galeria Blackwood, foi substituída por uma réplica quase perfeita.",
        [("Sofia Bennett", "Curadora", "A obra passou por restauro, mas ninguém autorizou qualquer troca."),
         ("Emma Collins", "Assistente", "Recebi a documentação das obras, não as manuseei."),
         ("James Walker", "Segurança", "A galeria esteve protegida durante toda a noite."),
         ("Daniel Mercer", "Sócio", "Nem sequer acompanho o inventário da galeria.")],
        ["Galeria", "Arquivo", "Sala de Segurança", "Escritório"],
        [("Galeria", "Fotografia de catálogo", "Detalhe do original", "A imagem anterior ao restauro mostra um pequeno detalhe ausente na pintura exposta."),
         ("Arquivo", "Ficha de conservação", "Troca recente", "Uma análise de conservação confirma que a obra exposta é uma cópia recente."),
         ("Galeria", "Autorização de transporte", "Assinatura de Sofia", "Sofia autorizou retirar a obra original para restauro às 21h20, fora do horário previsto."),
         ("Sala de Segurança", "Registo de movimentações", "Carrinho da curadora", "O carrinho atribuído a Sofia atravessou a saída de serviço às 21h35."),
         ("Escritório", "Correspondência impressa", "Venda clandestina", "Uma mensagem dirigida a Sofia combina a compra de uma pintura com os detalhes exatos de Nocturne."),
         ("Arquivo", "Guia de transporte", "Envio identificado", "Uma guia assinada por Sofia regista o envio de uma caixa com a identificação da obra original.")],
        [("Galeria", "Nota de restauro", "Pincéis novos", "Foram comprados pincéis novos para a equipa de conservação."),
         ("Escritório", "Mapa de exposições", "Agenda da galeria", "A próxima exposição estava prevista para o mês seguinte.")],
        [("Sofia Bennett", "P3", "Porque transportou a pintura tão tarde?", "Quis evitar perturbar os visitantes durante o dia."),
         ("James Walker", "P4", "Quem movimentou o carrinho?", "O registo identifica a zona e o carrinho, mas não mostra o conteúdo da caixa."),
         ("Sofia Bennett", "P6", "Porque assinou esta guia de envio?", "Não tenho uma explicação para essa identificação na guia.")],
        "Sofia Bennett", "Vender clandestinamente a pintura original",
        ["Impedir a reunião da empresa", "Esconder transferências financeiras"],
        [("P5", "P6"), ("P3", "P6")],
        "Sofia substituiu Nocturne por uma cópia durante o restauro e preparou o envio clandestino do original. A pintura é localizada antes de chegar ao comprador."
    ),
    make_case(
        "R2", "O Roubo Digital", "Roubo",
        "O alarme da galeria ficou desligado durante onze minutos. Quando voltou a funcionar, a pintura Nocturne tinha desaparecido.",
        [("Lucas Reed", "Técnico informático", "Não fiz nenhuma intervenção noturna no alarme da galeria."),
         ("Sofia Bennett", "Curadora", "A pintura estava no lugar quando saí."),
         ("James Walker", "Chefe de segurança", "A falha pareceu-me uma avaria, por isso pedi um relatório."),
         ("Oliver Blackwood", "Familiar", "Não tenho qualquer interesse naquela pintura.")],
        ["Galeria", "Sala de Segurança", "Garagem", "Arquivo"],
        [("Galeria", "Painel de alarme", "Onze minutos sem alarme", "O alarme esteve desativado entre as 23h12 e as 23h23."),
         ("Sala de Segurança", "Histórico técnico", "Credenciais de Lucas", "A desativação foi realizada com as credenciais de manutenção atribuídas a Lucas."),
         ("Arquivo", "Ordem de serviço", "Nenhuma manutenção autorizada", "Não existia qualquer intervenção de manutenção aprovada para aquela noite."),
         ("Garagem", "Câmara do portão", "Veículo de Lucas", "Às 23h24, o veículo de Lucas saiu com uma embalagem comprida na mala."),
         ("Garagem", "Material encontrado", "Embalagem do quadro", "O veículo de Lucas continha uma embalagem com a etiqueta de inventário da pintura roubada."),
         ("Arquivo", "Mensagem recuperada", "Proposta de venda", "Uma mensagem escrita por Lucas oferece Nocturne a um comprador e indica a data do desaparecimento.")],
        [("Galeria", "Folheto da exposição", "Descrição da pintura", "Nocturne mede 90 por 60 centímetros."),
         ("Sala de Segurança", "Livro de turnos", "Mudança de turno", "A passagem de turno decorreu normalmente às 22h00.")],
        [("Lucas Reed", "P2", "Porque foram utilizadas as suas credenciais?", "Podem ter usado a minha palavra-passe. Não fui eu."),
         ("James Walker", "P3", "Havia alguma intervenção prevista?", "Não. Por isso estranhei a desativação do sistema."),
         ("Lucas Reed", "P5", "Porque estava no seu carro esta embalagem?", "Era material de manutenção... Não reparei na etiqueta.")],
        "Lucas Reed", "Vender a pintura roubada para obter dinheiro",
        ["Destruir documentos familiares", "Impedir uma auditoria"],
        [("P4", "P5"), ("P5", "P6")],
        "Lucas desativou o alarme usando a sua conta técnica, retirou Nocturne e transportou-a no carro para a vender. A etiqueta e a mensagem permitem reconstruir o roubo."
    ),
    make_case(
        "R3", "O Vigilante", "Roubo",
        "A pintura Nocturne desapareceu sem que o relatório de segurança assinalasse qualquer incidente.",
        [("James Walker", "Chefe de segurança", "Não houve qualquer intrusão durante o meu turno."),
         ("Lucas Reed", "Técnico informático", "Não me pediram intervenções nos sistemas."),
         ("Sofia Bennett", "Curadora", "A obra estava corretamente inventariada."),
         ("Daniel Mercer", "Sócio", "Só soube do desaparecimento no dia seguinte.")],
        ["Galeria", "Sala de Segurança", "Garagem", "Escritório"],
        [("Sala de Segurança", "Relatório noturno", "Relatório sem incidentes", "James assinou um relatório que declara não ter ocorrido qualquer incidente."),
         ("Sala de Segurança", "Registo da consola", "Interrupção manual", "A gravação foi interrompida manualmente na consola autenticada por James."),
         ("Galeria", "Livro de chaves", "Chave de transporte", "James levantou uma chave usada na movimentação de obras às 23h05."),
         ("Galeria", "Inventário", "Caixa desaparecida", "Uma caixa de transporte com o tamanho de Nocturne não regressou ao inventário."),
         ("Garagem", "Armário de segurança", "Quadro escondido", "A caixa com Nocturne foi encontrada no armário pessoal de James, cuja única chave estava com ele."),
         ("Escritório", "Carta pessoal", "Dívida urgente", "Uma carta dirigida a James exige o pagamento de uma dívida nos próximos dias.")],
        [("Garagem", "Livro de manutenção", "Veículo reparado", "Uma viatura de serviço teve uma revisão nessa semana."),
         ("Escritório", "Mapa de horários", "Reunião de direção", "Havia uma reunião da direção agendada para a manhã seguinte.")],
        [("James Walker", "P1", "Porque não registou o desaparecimento?", "Ninguém me comunicou qualquer problema durante a noite."),
         ("Lucas Reed", "P2", "Foi uma falha automática?", "Não. O registo mostra uma ação manual na consola do segurança."),
         ("James Walker", "P5", "Como explica a pintura no seu armário?", "Não sei quem colocou aquilo lá. O armário costuma estar fechado.")],
        "James Walker", "Roubar a pintura para pagar uma dívida",
        ["Sabotar a apresentação Aurora", "Esconder um contrato alterado"],
        [("P3", "P5"), ("P2", "P5")],
        "James aproveitou o seu acesso à segurança para retirar Nocturne, escondeu-a no armário pessoal e registou falsamente uma noite sem incidentes."
    ),
    make_case(
        "S1", "O Relatório Desaparecido", "Sabotagem",
        "Antes da apresentação do Projeto Aurora, um relatório financeiro foi substituído por outro com valores adulterados.",
        [("Daniel Mercer", "Sócio", "As diferenças devem ser um erro de exportação."),
         ("Emma Collins", "Assistente", "Recebi uma ordem para atualizar os slides pouco antes da reunião."),
         ("Lucas Reed", "Técnico informático", "Não há sinais de falha no servidor."),
         ("James Walker", "Segurança", "Não reparei em nenhuma entrada não autorizada.")],
        ["Escritório", "Arquivo", "Sala de Segurança", "Garagem"],
        [("Arquivo", "Cópia de segurança", "Valores originais", "A cópia anterior do relatório contém valores diferentes dos apresentados."),
         ("Sala de Segurança", "Histórico de edições", "Conta de Daniel", "A alteração foi gravada através da conta de Daniel às 20h15."),
         ("Escritório", "Registo do computador", "Sessão de Daniel", "O computador do escritório de Daniel iniciou essa sessão, confirmada pelo seu acesso pessoal."),
         ("Escritório", "Dispositivo USB", "Tabelas alteradas", "Uma pen USB na gaveta fechada de Daniel contém as tabelas adulteradas."),
         ("Arquivo", "Notas da auditoria", "Auditoria iminente", "O auditor preparava uma verificação às operações financeiras supervisionadas por Daniel."),
         ("Escritório", "Mensagem enviada", "Pedido urgente a Emma", "Daniel pediu a Emma que substituísse imediatamente os slides, sem mostrar as alterações.")],
        [("Garagem", "Registo de viaturas", "Visita de fornecedor", "Um fornecedor esteve na garagem durante a tarde."),
         ("Arquivo", "Caixa de papel", "Material de impressão", "As reservas de papel foram renovadas antes do evento.")],
        [("Daniel Mercer", "P2", "Porque editou o relatório?", "Talvez tenha aberto o documento. Não me lembro de ter alterado valores."),
         ("Emma Collins", "P6", "Recebeu instruções para substituir o relatório?", "Sim. Daniel pediu-me para atualizar os slides sem verificar as tabelas."),
         ("Daniel Mercer", "P4", "Porque tem as tabelas adulteradas na gaveta?", "Guardei uma cópia para conferir. Isso não prova intenção.")],
        "Daniel Mercer", "Esconder irregularidades financeiras antes da auditoria",
        ["Destruir uma obra de arte", "Impedir uma venda familiar"],
        [("P2", "P4"), ("P3", "P4")],
        "Daniel preparou os valores falsos e tentou substituí-los no relatório antes da apresentação. A cópia original permite restabelecer os dados verdadeiros."
    ),
    make_case(
        "S2", "A Falha Programada", "Sabotagem",
        "A demonstração tecnológica do Projeto Aurora falhou durante a apresentação. A equipa suspeita de sabotagem.",
        [("Lucas Reed", "Técnico informático", "A falha só pode ter sido um erro dos equipamentos."),
         ("Sofia Bennett", "Curadora", "Acompanhei a montagem dos expositores, não a parte técnica."),
         ("James Walker", "Segurança", "Os equipamentos estavam protegidos."),
         ("Emma Collins", "Assistente", "A apresentação estava pronta no dia anterior.")],
        ["Galeria", "Escritório", "Sala de Segurança", "Arquivo"],
        [("Galeria", "Ecrã de diagnóstico", "Configuração alterada", "O diagnóstico indica que a demonstração foi interrompida por uma definição modificada manualmente."),
         ("Sala de Segurança", "Histórico da conta", "Conta técnica de Lucas", "A alteração foi realizada com a conta técnica atribuída a Lucas."),
         ("Galeria", "Registo de presença", "Visita ao equipamento", "A câmara mostra Lucas a operar a consola imediatamente antes da alteração registada."),
         ("Arquivo", "Ordem de trabalho", "Intervenção não autorizada", "Não existia autorização para modificar as definições no dia do evento."),
         ("Escritório", "Proposta comercial", "Assistência de Lucas", "Lucas enviara uma proposta de assistência paga para resolver precisamente esta falha."),
         ("Arquivo", "Cópia da configuração", "Cópia anterior", "A cópia de segurança confirma que o equipamento funcionava antes da alteração manual.")],
        [("Galeria", "Lista de convidados", "Participantes da apresentação", "Foram convidados vários parceiros para assistir à demonstração."),
         ("Escritório", "Agenda", "Horário do evento", "A demonstração estava marcada para as 16h00.")],
        [("Lucas Reed", "P2", "Porque foi usada a sua conta?", "É a conta que usamos para testes técnicos. Pode ter sido alguém da equipa."),
         ("James Walker", "P3", "Quem esteve na consola?", "A gravação mostra Lucas a trabalhar sozinho nesse equipamento."),
         ("Lucas Reed", "P5", "Porque ofereceu assistência para a mesma avaria?", "É uma coincidência. São problemas comuns nestes sistemas.")],
        "Lucas Reed", "Criar uma avaria para vender assistência técnica",
        ["Roubar a pintura da galeria", "Impedir uma herança familiar"],
        [("P2", "P3"), ("P3", "P5")],
        "Lucas modificou o equipamento deliberadamente para provocar uma falha e valorizar a sua proposta de manutenção. O sistema é restaurado a partir da cópia anterior."
    ),
    make_case(
        "S3", "A Última Apresentação", "Sabotagem",
        "Uma apresentação sobre património da família Blackwood foi interrompida porque os documentos essenciais desapareceram do computador.",
        [("Oliver Blackwood", "Irmão", "Não concordo com a venda, mas não toquei nos ficheiros."),
         ("Emma Collins", "Assistente", "Os documentos estavam disponíveis quando preparei a reunião."),
         ("Daniel Mercer", "Sócio", "A empresa precisava de apresentar aqueles números."),
         ("Lucas Reed", "Técnico informático", "O computador não apresenta qualquer avaria.")],
        ["Escritório", "Arquivo", "Sala de Segurança", "Garagem"],
        [("Escritório", "Mensagens familiares", "Oposição à venda", "Oliver escreveu que impediria a venda do terreno a qualquer custo."),
         ("Sala de Segurança", "Registo de entrada", "Acesso de Oliver", "O cartão pessoal de Oliver abriu a sala de apresentações às 18h52."),
         ("Escritório", "Histórico USB", "Pen USB ligada", "Um dispositivo externo foi ligado ao computador às 18h55, pouco antes do desaparecimento dos ficheiros."),
         ("Arquivo", "Inventário de dispositivos", "Identificador de Oliver", "O identificador do dispositivo ligado coincide com a pen USB inventariada em nome de Oliver."),
         ("Garagem", "Mochila guardada", "Ficheiros encontrados", "A pen de Oliver foi encontrada numa mochila pessoal guardada no seu veículo, contendo os ficheiros desaparecidos."),
         ("Arquivo", "Cópia de segurança", "Documentos originais", "A cópia das 18h00 confirma que os ficheiros existiam antes da entrada de Oliver." )],
        [("Escritório", "Programa do evento", "Ordem das intervenções", "O anúncio estava previsto para as 19h30."),
         ("Garagem", "Registo da limpeza", "Limpeza habitual", "A garagem foi limpa durante a manhã." )],
        [("Oliver Blackwood", "P1", "Porque queria impedir a venda?", "Aquela propriedade pertence à história da nossa família."),
         ("Lucas Reed", "P3", "O que aconteceu aos ficheiros?", "Foram copiados para uma pen. O computador não teve nenhuma falha."),
         ("Oliver Blackwood", "P5", "Porque estavam os ficheiros na sua pen?", "Não devia ter levado aqueles documentos. Não queria que a venda avançasse.")],
        "Oliver Blackwood", "Impedir o anúncio da venda de património familiar",
        ["Vender serviços informáticos", "Esconder transferências financeiras"],
        [("P4", "P5"), ("P2", "P5")],
        "Oliver retirou os documentos essenciais para impedir a apresentação e atrasar a venda. Os ficheiros são recuperados e a reunião pode prosseguir."
    ),
]

CASE_BY_ID = {case["id"]: case for case in CASES}
SCENE_META = {
    "Escritório": ("◈", "Contratos, notas e correspondência"),
    "Arquivo": ("▤", "Documentação e registos antigos"),
    "Sala de Segurança": ("⌘", "Câmaras e acessos eletrónicos"),
    "Garagem": ("▱", "Veículos e equipamento"),
    "Galeria": ("◇", "Obras de arte e inventários"),
}


# -----------------------------------------------------------------------------
# JOGO 2 — 30 perguntas: 10 fáceis, 10 médias e 10 difíceis.
# (id, dificuldade, título, facto, A, B, C, resposta, provas possíveis,
#  índice da prova correta, explicação)
# -----------------------------------------------------------------------------

# ## JOGO 2 — SALA DE INTERROGATÓRIO: banco de 30 perguntas
RAW_QUESTIONS = [
 (1,"Fácil","A porta do arquivo","O sensor confirma que a porta do arquivo não abriu entre as 20h e as 21h.","Entrei no arquivo às 19h45.","Abri a porta e entrei no arquivo às 20h30.","Passei pelo corredor às 20h40.","B",["O calendário de reuniões","O registo do sensor da porta","O recibo do estacionamento"],1,"Nenhuma abertura ocorreu entre as 20h e as 21h."),
 (2,"Fácil","O apagão","A galeria esteve sem eletricidade das 21h às 22h; as luzes do teto não funcionaram.","Às 21h30 as luzes do teto estavam acesas.","Às 21h45 usei a lanterna do telemóvel.","Saí às 20h50.","A",["A lista de visitantes","O horário da equipa","O registo do corte de eletricidade"],2,"As luzes do teto não podiam estar acesas às 21h30."),
 (3,"Fácil","A noite de chuva","O registo meteorológico indica que a chuva começou às 23h30 e não choveu antes.","Às 23h00 estava vento.","Às 23h45 começou a chover quando regressava.","Às 23h10 apanhei chuva ao sair do edifício.","C",["O registo meteorológico","O horário da receção","Uma fatura da galeria"],0,"Às 23h10 ainda não tinha começado a chover."),
 (4,"Fácil","O alarme","A sirene foi ativada pela primeira vez às 22h15.","Ouvi a sirene às 22h20.","Ouvi essa sirene às 21h55.","Trabalhei no primeiro piso às 22h.","B",["A agenda do diretor","A hora de ativação da sirene","O livro de visitas"],1,"Não existiu qualquer ativação às 21h55."),
 (5,"Fácil","Entrada proibida","Os sensores confirmam que ninguém entrou no edifício entre as 20h e as 22h.","Entrei no edifício às 20h30.","Saí às 19h55.","Esperei na rua às 21h.","A",["Os sensores de entrada","A lista de material de escritório","O inventário das viaturas"],0,"Não houve entradas nesse intervalo."),
 (6,"Fácil","O contrato original","A única cópia física original chegou ao arquivo às 16h.","Vi uma caixa destinada ao contrato às 15h.","Consultei esse original no arquivo às 15h30.","Registei a entrega às 16h10.","B",["O relatório da manutenção","O recibo da cafeteria","O registo de entrega do original"],2,"O original não estava lá às 15h30."),
 (7,"Fácil","O portão da garagem","Entre as 17h e as 18h, o portão abriu apenas às 17h45.","O portão abriu às 17h45.","Estive na garagem às 17h30.","Saí de carro por esse portão às 17h15.","C",["A escala de serviço","O registo de abertura do portão","Uma fatura de combustível"],1,"Não houve abertura às 17h15."),
 (8,"Fácil","O cofre selado","O cofre foi selado às 9h e permaneceu intacto, sem acesso ao interior, até às 13h.","Retirei um documento do cofre às 11h.","Vi o cofre selado às 12h.","Entreguei uma pasta às 11h.","A",["O termo de selagem e vigilância","O mapa do edifício","A agenda de reuniões"],0,"O interior do cofre não foi aberto durante o período."),
 (9,"Fácil","Servidor indisponível","O servidor de email da empresa esteve indisponível entre as 10h e as 11h.","Escrevi um email às 10h30 mas não o enviei.","Enviei um email através desse servidor às 10h30.","Enviei um email às 11h10.","B",["O relatório de limpeza","O diário da galeria","O registo de indisponibilidade do servidor"],2,"O servidor não aceitava envios às 10h30."),
 (10,"Fácil","Elevador avariado","O único elevador esteve imobilizado das 18h às 20h.","Usei as escadas às 19h.","Estive no segundo piso desde as 17h.","Subi de elevador às 19h15.","C",["O livro de visitas","O relatório de avaria do elevador","A nota de compras"],1,"O elevador não podia transportar ninguém às 19h15."),
 (11,"Média","Cartão perdido","O sistema registou a utilização do cartão B-17 às 22h12.","O cartão B-17 não foi usado nesse dia.","Perdi o cartão B-17 antes das 22h.","Vi a porta aberta pouco depois das 22h12.","A",["O registo de acessos do cartão","Uma fotografia do corredor","A lista de correspondência"],0,"O cartão foi utilizado, ainda que não saibamos por quem."),
 (12,"Média","Trajeto impossível","Uma pessoa saiu do escritório às 14h20. O percurso até à galeria demora pelo menos 25 minutos.","Saí do escritório às 14h20.","Saí às 14h20 e cheguei à galeria às 14h35.","Cheguei à galeria às 15h.","B",["A agenda das reuniões","O tempo mínimo do percurso e a hora de saída","O inventário de quadros"],1,"Chegar em 15 minutos seria impossível; o mínimo é 25."),
 (13,"Média","A chamada","Uma chamada começou às 19h04 e terminou às 19h16, segundo a operadora.","Ainda estava nessa chamada às 19h10.","Enviei uma mensagem às 19h20.","Terminei essa chamada às 19h06.","C",["Uma nota do arquivo","A câmara da garagem","O registo da operadora"],2,"A chamada acabou às 19h16."),
 (14,"Média","O armário das chaves","Havia oito chaves no armário às 12h, sem retiradas nem entradas até às 14h.","Às 13h o armário tinha dez chaves.","Às 12h tinha oito chaves.","Às 13h30 continuava a ter oito.","A",["Um folheto da galeria","O inventário e o registo de movimentos","O horário do vigilante"],1,"Sem movimentos, o total permaneceu em oito."),
 (15,"Média","Duas pessoas","Duas pessoas entraram na sala às 18h15; a única saída não abriu até às 18h45.","Entrei acompanhado às 18h15.","Estive completamente sozinho na sala às 18h30.","Havia pelo menos duas pessoas às 18h30.","B",["O sensor da única saída","A fatura de táxi","Um documento financeiro"],0,"As duas pessoas ainda estavam dentro às 18h30."),
 (16,"Média","Ficheiro intacto","Um documento foi criado às 17h e não sofreu alterações até às 19h.","Consultei-o às 17h20.","Imprimi-o às 18h50.","Editei o conteúdo às 18h10.","C",["A planta da galeria","A escala da segurança","O histórico de alterações do ficheiro"],2,"Editar o conteúdo teria gerado uma alteração no histórico."),
 (17,"Média","Laboratório fechado","A porta do laboratório não abriu entre as 16h e as 17h30.","Entrei às 17h45.","Esperei junto à porta às 17h.","Abri a porta e entrei às 16h45.","C",["O bilhete de entrada","O sensor da porta do laboratório","O relatório meteorológico"],1,"A porta esteve fechada durante todo o intervalo."),
 (18,"Média","Entrega atrasada","A encomenda BX-204 chegou pela primeira vez à receção no dia 12 às 10h.","Recebi-a na receção no dia 11 às 18h.","Perguntei por ela na receção no dia 11.","Assinei a receção no dia 12 às 10h10.","A",["O comprovativo de primeira entrega","Uma folha de despesas","A autorização de férias"],0,"Não podia ter sido recebida na receção no dia anterior à chegada."),
 (19,"Média","Servidor desligado","O servidor de armazenamento não aceitava carregamentos das 13h às 14h.","Guardei um ficheiro no meu computador às 13h15.","Carreguei um ficheiro nesse servidor às 13h30.","Carreguei um ficheiro às 14h10.","B",["O horário da cafetaria","O relatório de indisponibilidade do servidor","O registo da garagem"],1,"O servidor rejeitava carregamentos às 13h30."),
 (20,"Média","Duas aberturas","Entre as 20h e as 20h15, uma porta abriu apenas às 20h05 e às 20h08.","Ouvi a porta abrir às 20h05.","Passei pelo corredor às 20h02.","Abri essa porta às 20h02.","C",["A lista de convidados","Uma carta de Oliver","O histórico eletrónico da porta"],2,"Não existiu qualquer abertura às 20h02."),
 (21,"Difícil","Entrada secreta","A única porta do arquivo permaneceu fechada das 21h às 21h40; a primeira abertura foi às 21h42.","Estive no corredor às 21h25.","Abri essa porta e entrei às 21h32.","Saí do arquivo às 21h50.","B",["O registo da porta única","Uma fotografia de um carro","A ordem de pagamento"],0,"A porta não abriu às 21h32; a primeira abertura foi às 21h42."),
 (22,"Difícil","Dois lugares","Uma pessoa saiu do escritório às 9h58. O percurso à galeria leva pelo menos 25 minutos.","Saí às 9h58 e cheguei às 10h12.","Cheguei à galeria às 10h28.","O meu percurso durou mais de 20 minutos.","A",["O inventário do arquivo","A hora de saída e o tempo mínimo de deslocação","O horário de almoço"],1,"A chegada mais cedo seria às 10h23, não às 10h12."),
 (23,"Difícil","Escuridão e sirene","A eletricidade falhou das 22h10 às 22h50. A sirene funcionava por bateria independente.","Ouvi a sirene às 22h20.","Usei uma lanterna às 22h40.","As luzes do teto estavam acesas às 22h30.","C",["Uma folha de presenças","O registo de viaturas","O relatório do apagão e alimentação da sirene"],2,"A sirene podia funcionar, mas as luzes do teto não."),
 (24,"Difícil","Assinatura impossível","O único contrato original foi assinado às 19h05. Uma gravação contínua comprova que esteve sem assinatura antes.","Vi o original já assinado às 18h55.","Li um rascunho sem assinatura às 18h40.","Guardei o original às 19h20.","A",["A gravação do momento da assinatura","O horário do estacionamento","A lista de quadros"],0,"O original ainda estava sem assinatura às 18h55."),
 (25,"Difícil","Sem saída","O elevador não funcionou das 19h às 20h; as únicas escadas fecharam das 19h10 às 19h50.","Permaneci no rés do chão às 19h30.","Saí do rés do chão e subi ao terceiro piso às 19h30.","Estive no terceiro piso desde as 18h50.","B",["Uma fotografia do jardim","Os relatórios do elevador e das escadas","O documento de compra"],1,"Às 19h30 nenhuma ligação entre pisos estava disponível."),
 (26,"Difícil","Percurso suspeito","A câmara mostra uma pessoa na garagem até às 18h25. O percurso até à galeria demora pelo menos 25 minutos.","Vi essa pessoa na garagem às 18h20.","Vi essa pessoa na galeria às 19h.","Vi essa pessoa na galeria às 18h35.","C",["O bilhete do museu","A ordem de transporte","A gravação da garagem e o tempo do trajeto"],2,"A chegada mais cedo seria às 18h50."),
 (27,"Difícil","Ficheiro desaparecido","Um ficheiro foi criado às 20h, permaneceu intacto e foi eliminado às 21h10; o histórico completo foi guardado.","Li o ficheiro às 20h30.","Editei o conteúdo às 21h05.","Copiei o ficheiro às 20h55.","B",["O histórico completo do ficheiro","Um recibo da garagem","O horário de visitas"],0,"Não há qualquer alteração registada antes de ser eliminado."),
 (28,"Difícil","Prova selada","Um armário foi selado às 10h com duas pen USB dentro e permaneceu sob vigilância com o selo intacto até às 12h.","Retirei uma pen do armário às 11h30.","Fotografei o selo às 11h.","Vi o armário do corredor às 11h40.","A",["Um mapa dos pisos","O termo de selagem e a vigilância","O catálogo de exposição"],1,"Não se podia retirar uma pen sem abrir o armário selado."),
 (29,"Difícil","Reunião clandestina","Duas pessoas entraram numa sala às 23h. A sala só tem uma porta e ninguém saiu antes das 23h30.","Ouvi duas pessoas às 23h10.","Entrei acompanhado às 23h.","Estive completamente sozinho na sala às 23h15.","C",["Uma agenda antiga","O contrato da galeria","O registo de entrada e da única saída"],2,"Pelo menos duas pessoas continuaram na sala às 23h15."),
 (30,"Difícil","A fotografia","Um módulo foi instalado no projetor às 20h40 e nunca estivera ligado ao equipamento antes dessa hora.","Fotografei o módulo já instalado às 20h25.","Assinei a ordem às 20h15.","Vi o módulo instalado às 21h.","A",["A gravação e o registo da instalação","Uma mensagem familiar","O inventário dos veículos"],0,"Antes das 20h40, o módulo ainda não estava instalado.")
]

QUESTIONS = [dict(zip(("id", "level", "title", "fact", "A", "B", "C", "answer", "proofs", "correct_proof", "explanation"), q)) for q in RAW_QUESTIONS]


def draw_questions():
    """Uma partida: 3 fáceis, 3 médias, 2 difíceis, nesta ordem."""
    return (random.sample([q for q in QUESTIONS if q["level"] == "Fácil"], 3)
            + random.sample([q for q in QUESTIONS if q["level"] == "Média"], 3)
            + random.sample([q for q in QUESTIONS if q["level"] == "Difícil"], 2))

# %% [markdown]
# # PARTE 2 — DESAFIOS DE LÓGICA
# Conteúdo do antigo puzzles.py. Puzzles utilizados na recolha de provas do Detetive X.
# %%


def puzzle(question, choices, correct, explanation):
    return {"question":question, "choices":choices, "correct":correct, "explanation":explanation}

PUZZLES = {
 "D1":{
  "P2":puzzle("No registo de acessos, qual é a entrada que liga Daniel ao arquivo?",["Cartão de Daniel — 22h38", "Cartão de Emma — 20h38", "Cartão de James — 23h59"],0,"O cartão de Daniel abriu o arquivo às 22h38."),
  "P3":puzzle("Que elemento da fechadura permite associar o encerramento a uma pessoa?",["O número da sala", "A chave individual usada às 22h43", "A cor da porta"],1,"A chave eletrónica individual identifica Daniel como utilizador."),
  "P5":puzzle("Ao comparar a entrada e a saída no vídeo, quem regressa sem Alexander?",["Oliver", "Daniel", "James"],1,"Daniel entrou acompanhado e regressou sozinho."),
  "P6":puzzle("A saída do veículo ocorreu em que relação ao fecho da sala?",["Antes de fechar", "No dia seguinte", "Depois do fecho"],2,"O veículo saiu às 22h49, depois do fecho às 22h43.")
 },
 "D2":{
  "P2":puzzle("Segundo a mensagem encontrada, onde era o encontro marcado?",["Na galeria às 20h15", "Na garagem às 21h45", "No arquivo às 23h30"],1,"Oliver convocou Alexander para a garagem às 21h45."),
  "P3":puzzle("Que registo prova o fecho da divisão de manutenção?",["Chave pessoal de Oliver, 21h51", "Cartão de James, 22h50", "Alarme de incêndio, 21h01"],0,"O sistema identifica a chave de Oliver."),
  "P5":puzzle("Quem aparece a deixar a área de manutenção sem companhia?",["Alexander", "Oliver", "Emma"],1,"Oliver sai sozinho, enquanto Alexander não volta a aparecer."),
  "P6":puzzle("Qual era a consequência da venda para Oliver?",["Receberia uma obra de arte", "Passaria a chefe de segurança", "Perderia direitos de utilização do terreno"],2,"O contrato fornece um possível motivo familiar.")
 },
 "D3":{
  "P2":puzzle("Que instrução recebeu Alexander no bilhete?",["Ir à sala reservada do arquivo", "Sair pela garagem", "Cancelar a reunião"],0,"O bilhete encaminhava Alexander para a sala reservada."),
  "P3":puzzle("Qual é o computador associado à impressão do bilhete?",["O da sala de segurança", "O de Emma", "O de Oliver"],1,"A impressora regista o computador de Emma às 20h31."),
  "P5":puzzle("O registo da fechadura aponta para quem?",["Daniel", "James", "Emma"],2,"Emma usou a chave pessoal para fechar a sala."),
  "P6":puzzle("Na mensagem de voz, quem indicou o local a Alexander?",["Emma", "Oliver", "Lucas"],0,"Alexander refere explicitamente a indicação de Emma.")
 },
 "R1":{
  "P2":puzzle("O que demonstra a ficha de conservação?",["Que a obra não foi visitada", "Que a pintura exposta é uma cópia recente", "Que o alarme esteve sempre ligado"],1,"A análise de conservação identifica uma cópia."),
  "P3":puzzle("Quem assinou a retirada da obra fora do horário?",["Sofia", "James", "Daniel"],0,"A autorização de transporte está assinada por Sofia."),
  "P5":puzzle("Que elemento torna a mensagem suspeita?",["Refere uma pintura com as características de Nocturne", "Menciona apenas o horário da limpeza", "Não tem destinatário"],0,"A mensagem combina uma venda com os detalhes exatos da obra."),
  "P6":puzzle("O que associa a guia de transporte a Sofia?",["O carimbo do museu", "A assinatura dela", "Uma impressão digital não identificada"],1,"Sofia assinou o envio de uma caixa com a identificação da pintura.")
 },
 "R2":{
  "P2":puzzle("De quem são as credenciais usadas para desativar o alarme?",["James", "Lucas", "Sofia"],1,"O histórico técnico identifica credenciais atribuídas a Lucas."),
  "P3":puzzle("A intervenção noturna estava autorizada?",["Sim, por Daniel", "Sim, por Sofia", "Não havia nenhuma ordem aprovada"],2,"Não existia autorização de manutenção naquele horário."),
  "P4":puzzle("Que movimento coincide com o fim da falha de segurança?",["O carro de Lucas saiu às 23h24", "A biblioteca abriu às 23h24", "Oliver entrou às 22h15"],0,"O veículo de Lucas saiu imediatamente depois de o alarme voltar a funcionar."),
  "P5":puzzle("Qual é a ligação mais forte entre a embalagem e o roubo?",["A cor da mala", "A etiqueta de inventário da pintura", "O formato das rodas"],1,"A etiqueta liga o material de transporte diretamente à obra desaparecida.")
 },
 "R3":{
  "P2":puzzle("Onde foi interrompida manualmente a gravação?",["Numa consola autenticada por James", "No telemóvel de Oliver", "Na impressora da galeria"],0,"O registo aponta para a consola atribuída a James."),
  "P3":puzzle("Para que servia a chave levantada por James?",["Abrir a caixa de correio", "Movimentar obras da galeria", "Abrir a cozinha"],1,"A chave permite aceder ao transporte de obras."),
  "P5":puzzle("Onde foi encontrada a caixa com a pintura?",["Na sala de reuniões", "No veículo de Emma", "No armário pessoal de James"],2,"A caixa estava no armário de James, ao qual só ele tinha chave."),
  "P6":puzzle("Que problema pessoal aparece na carta?",["Uma dívida com prazo de pagamento", "Uma mudança de residência", "Um convite para jantar"],0,"A dívida urgente é um possível motivo financeiro.")
 },
 "S1":{
  "P2":puzzle("Qual conta gravou as alterações ao relatório?",["Emma às 18h45", "Daniel às 20h15", "Lucas às 23h30"],1,"O histórico regista a conta de Daniel às 20h15."),
  "P3":puzzle("Que computador iniciou essa sessão?",["O do escritório de Daniel", "O da galeria", "O computador da receção"],0,"A sessão ocorreu no computador do escritório de Daniel."),
  "P4":puzzle("Onde foi encontrada a cópia das tabelas adulteradas?",["Num email de Oliver", "Num servidor público", "Numa pen na gaveta fechada de Daniel"],2,"A pen foi encontrada num espaço privado de Daniel."),
  "P5":puzzle("Que área seria alvo da auditoria?",["As compras da galeria", "As operações financeiras supervisionadas por Daniel", "Os turnos da garagem"],1,"O risco da auditoria ajuda a explicar o motivo.")
 },
 "S2":{
  "P2":puzzle("A quem estava atribuída a conta técnica utilizada?",["Lucas", "Sofia", "James"],0,"O histórico apresenta a conta técnica atribuída a Lucas."),
  "P3":puzzle("Quem aparece a operar a consola imediatamente antes da alteração?",["Emma", "Lucas", "Oliver"],1,"A câmara regista a presença de Lucas na consola."),
  "P4":puzzle("Existia autorização para alterar as definições?",["Sim, para Oliver", "Sim, para Daniel", "Não existia qualquer autorização"],2,"A ordem de trabalho exclui uma intervenção legítima."),
  "P5":puzzle("Que vantagem Lucas poderia retirar da falha?",["Vender assistência paga", "Receber uma herança", "Vender uma pintura"],0,"A proposta comercial corresponde ao tipo exato de avaria.")
 },
 "S3":{
  "P2":puzzle("Qual foi o acesso registado antes do incidente?",["Daniel, 20h00", "Oliver, 18h52", "James, 23h00"],1,"O cartão de Oliver abriu a sala de apresentações às 18h52."),
  "P3":puzzle("A que horas foi ligado o dispositivo externo?",["18h55", "17h15", "20h40"],0,"A pen USB foi ligada às 18h55, imediatamente antes de os ficheiros desaparecerem."),
  "P4":puzzle("O identificador do dispositivo corresponde a quem?",["Emma", "Daniel", "Oliver"],2,"O inventário associa a pen USB a Oliver."),
  "P5":puzzle("Onde estava guardado o dispositivo que continha os ficheiros?",["Na sala de segurança", "Numa mochila no veículo de Oliver", "No arquivo público"],1,"A pen com os ficheiros estava na mochila pessoal de Oliver.")
 }
}

# %% [markdown]
# # PARTE 3 — APLICAÇÃO WEB E OS TRÊS JOGOS
# Conteúdo do app.py. Interface, regras, pontuação e servidor Python.
# %%

ROOT = Path(__file__).resolve().parent
BASE_TEMPLATE = (ROOT / "index.html").read_text(encoding="utf-8")
HOME_PREVIEW = re.search(r'<!-- ECRA_INICIO -->(.*?)<!-- ECRA_FIM -->', BASE_TEMPLATE, flags=re.S).group(1)
# Os modelos HTML estão todos no index.html, em elementos <template>.
# O navegador não mostra esses templates diretamente. O Python escolhe o adequado.
VIEWS = {name: body for name, body in re.findall(
    r'<template id="view-([a-z_]+)">(.*?)</template>', BASE_TEMPLATE, flags=re.S)}


def tpl(name, **parts):
    """Preenche os marcadores [[NOME]] dos templates HTML.

    Textos vindos de utilizadores devem passar por E(...) antes de entrar aqui.
    As partes de HTML dinâmico são construídas pelas funções Python.
    """
    result = VIEWS[name]
    for key, value in parts.items():
        result = result.replace('[[%s]]' % key, str(value))
    if re.search(r'\[\[[A-Z_]+\]\]', result):
        raise ValueError('Faltam dados no template HTML: ' + name)
    return result

# ## JOGO 3 — O COFRE TRANCADO: limites por dificuldade
SAFE_LIMITS = {"facil": 16, "medio": 12, "dificil": 8}
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()

PEOPLE_IMAGES = {
    "Daniel Mercer": "daniel", "Emma Collins": "emma", "James Walker": "james",
    "Oliver Blackwood": "oliver", "Sofia Bennett": "sofia", "Lucas Reed": "lucas",
}
SCENES = {
    "Escritório": ("scene_office", "O lugar onde as decisões são tomadas."),
    "Arquivo": ("scene_archive", "Documentos antigos, registos e salas reservadas."),
    "Sala de Segurança": ("scene_security", "Gravações, cartões de acesso e relatórios."),
    "Garagem": ("scene_garage", "Veículos e movimentos noturnos."),
    "Galeria": ("scene_gallery", "Obras de arte e zonas de conservação."),
}
GFX_EVIDENCE = ["evidence_file", "evidence_note", "evidence_key", "evidence_cloth"]


def E(text):
    return html.escape(str(text), quote=True)


def asset(name):
    return f"/assets/{E(name)}.jpg"


def img_for_evidence(evidence):
    target = f"{evidence['object']} {evidence['title']}".lower()
    if any(s in target for s in ("câmara", "monitor", "imagem", "vídeo", "fotografia", "gravação")):
        return "evidence_cloth"
    if any(s in target for s in ("chave", "leitor", "fechadura", "portão", "cartão", "acesso")):
        return "evidence_key"
    if any(s in target for s in ("mensagem", "email", "nota", "bilhete", "carta", "correspondência")):
        return "evidence_note"
    return "evidence_file"


def new_state():
    return {
        "case_id": None, "case_deck": [], "found": set(), "confronted": set(),
        "asked": set(), "selected_suspect": "", "dialogue": "", "speaker": "",
        "penalty": 0, "wrong_accusations": 0, "solved_puzzles": set(),
        "flash": "", "flash_kind": "info", "last_clue": "", "deductions": set(), "wrong_deductions": set(),
        "notes": "", "result": None, "quiz": [], "quiz_index": 0,
        "quiz_witness": None, "quiz_proof": None, "quiz_score": 0,
        "quiz_results": [], "safe_level": "medio", "safe_code": random.randint(0, 999),
        "safe_guesses": [], "safe_won": False,
    }


def current_case(s):
    return CASE_BY_ID.get(s.get("case_id"))


def notify(s, message, kind="info"):
    s["flash"] = message
    s["flash_kind"] = kind


def new_case(s):
    if not s["case_deck"]:
        s["case_deck"] = list(CASE_BY_ID)
        random.shuffle(s["case_deck"])
        if s["case_id"] == s["case_deck"][-1] and len(s["case_deck"]) > 1:
            s["case_deck"][0], s["case_deck"][-1] = s["case_deck"][-1], s["case_deck"][0]
    cid = s["case_deck"].pop()
    c = CASE_BY_ID[cid]
    s.update(case_id=cid, found=set(), confronted=set(), asked=set(),
             motive_order=random.sample(c["motive_options"],len(c["motive_options"])),
             selected_suspect=c["suspects"][0][0], speaker=c["suspects"][0][0],
             dialogue=c["suspects"][0][2], penalty=0, wrong_accusations=0,
             solved_puzzles=set(), last_clue="", deductions=set(), wrong_deductions=set(), notes="", result=None)
    notify(s, f"Novo dossier atribuído: {c['title']}. Explora os locais e interroga os suspeitos.", "success")


def can_accuse(s):
    c = current_case(s)
    if not c: return False
    found = s["found"]
    return sum(x.startswith('P') for x in found) >= 4 and any(set(pair) <= found for pair in c['valid_pairs'])


def qualified_pair(c, a, b):
    return frozenset((a,b)) in {frozenset(x) for x in c["valid_pairs"]}


def btn(action, title, *, id="", cls="btn", extra="", icon="", disabled=False, fields=None):
    values={"action":action,"id":id}
    if fields: values.update(fields)
    inputs=''.join(f'<input type="hidden" name="{E(k)}" value="{E(v)}">' for k,v in values.items())
    icon_html = f'<span class="btn-icon">{E(icon)}</span>' if icon else ''
    return (f'<form method="post" action="/action" class="form-inline {E(extra)}">{inputs}'
            f'<button type="submit" class="{E(cls)}" {"disabled" if disabled else ""}>'
            f'{icon_html}{E(title)}</button></form>')


def link(url,title,klass="link-pill", icon=""):
    return f'<a href="{E(url)}" class="{E(klass)}">{f"<span>{E(icon)}</span> " if icon else ""}{E(title)}</a>'


def page_head(kicker,title,caption="",right=""):
    right_html = f'<div class="page-head-right">{right}</div>' if right else ''
    return (f'<div class="page-head"><div><div class="kicker">{E(kicker)}</div><h1>{E(title)}</h1>'
            f'<p>{E(caption)}</p></div>{right_html}</div>')


def progress_bar(value, max_value, style=""):
    pc=round(value*100/max(max_value,1))
    return f'<div class="meter {E(style)}"><i style="width:{pc}%"></i></div>'


def summary_counts(s):
    return sum(x.startswith('P') for x in s['found']), sum(x.startswith('S') for x in s['found'])


def detective_subnav(s,view):
    """Opções internas apenas quando o Detetive X tem uma investigação iniciada."""
    if not current_case(s):return ''
    options=[('case','Resumo do caso'),('locations','Locais'),('suspects','Suspeitos'),
             ('interrogate','Interrogatórios'),('evidence','Quadro de provas'),
             ('notes','Notas'),('accuse','Acusação final')]
    sub=''.join(f'<a href="/?view={name}" class="side-subitem {"selected" if (view==name or (view=="inspect" and name=="locations")) else ""}"><span class="subnav-dot"></span>{E(label)}</a>' for name,label in options)
    return '<div class="detective-subnav" aria-label="Opções internas do Detetive X"><div class="subnav-heading">DENTRO DO DETETIVE X</div>'+sub+'</div>'


def render_home(s):
    """A página inicial está escrita integralmente no index.html."""
    return HOME_PREVIEW


# ## JOGO 1 — Interfaces HTML da investigação (pasta views)
def render_case(s):
    c = current_case(s)
    if not c: return render_start_case(s)
    n, ns = summary_counts(s)
    suspects = ''.join(
        f'<a class="mini-suspect" href="/?view=interrogate&suspect={quote(p[0])}">'
        f'<img src="{asset(PEOPLE_IMAGES[p[0]])}" alt=""><span>{E(p[0])}</span>'
        f'<small>{E(p[1])}</small></a>' for p in c['suspects'])
    loc = ''.join(
        f'<a href="/?view=locations&scene={quote(scene)}" class="location-row">'
        f'<img src="{asset(SCENES[scene][0])}" alt=""><span><b>{E(scene)}</b>'
        f'<small>{E(SCENES[scene][1])}</small></span><span class="chevron">›</span></a>'
        for scene in c['locations'])
    recent = ''.join(
        f'<div class="evidence-line"><span class="evidence-dot"></span>'
        f'<b>{E(c["evidence"][eid]["title"])}</b></div>'
        for eid in list(sorted(s['found']))[-4:]
    ) or '<p class="muted">Ainda não encontraste provas. Começa por um local.</p>'
    return (page_head(f'DOSSIER {c["id"]} · {c["genre"]}',c['title'],c['intro'],
                      btn('new_case','Novo caso',cls='btn btn-mini btn-muted',icon='↻'))
            + tpl('case',SUSPECTS=suspects,PRINCIPAIS=n,SECUNDARIAS=ns,
                  CONFRONTOS=len(s['confronted']),LOCATIONS=loc,RECENT=recent,
                  TIP=E('Já podes apresentar uma acusação.' if can_accuse(s)
                        else 'A acusação só fica disponível com 4 provas principais e um par de provas relevante.')))


def render_start_case(s):
    return page_head('JOGO PRINCIPAL','Detetive X','Cada partida seleciona uma das nove investigações preparadas.') + tpl('start_case')


def render_suspects(s):
    c=current_case(s)
    if not c:return render_start_case(s)
    cards=''
    for person, role, initial in c['suspects']:
        cards+=(f'<article class="suspect-card"><div class="suspect-image">'
                f'<img src="{asset(PEOPLE_IMAGES[person])}" alt="Retrato de {E(person)}"></div>'
                f'<div class="suspect-info"><span class="tiny-label">SOB INVESTIGAÇÃO</span>'
                f'<h2>{E(person)}</h2><p class="role">{E(role)}</p>'
                f'<p class="quote">“{E(initial)}”</p>'
                +link('/?view=interrogate&suspect='+quote(person),'Interrogar','btn btn-outline','◉')
                +'</div></article>')
    return page_head('FICHAS PESSOAIS','Suspeitos',f'Quatro pessoas estão relacionadas com o caso {c["title"]}.')+tpl('suspects',CARDS=cards)


def render_locations(s,scene):
    c=current_case(s)
    if not c:return render_start_case(s)
    if not scene or scene not in c['locations']:
        cards=''
        for name in c['locations']:
            im,description=SCENES[name]
            total=sum(e['location']==name for e in c['evidence'].values())
            found=sum(eid in s['found'] for eid,e in c['evidence'].items() if e['location']==name)
            cards+=(f'<a href="/?view=locations&scene={quote(name)}" class="scene-card">'
                   f'<div class="scene-image" style="background-image:url({asset(im)})"></div>'
                   f'<div class="scene-caption"><span class="tiny-label">ÁREA INVESTIGÁVEL</span>'
                   f'<h2>{E(name)}</h2><p>{E(description)}</p><div class="scene-progress">'
                   f'{progress_bar(found,total)}<span>{found}/{total} elementos analisados</span>'
                   f'</div></div></a>')
        return page_head('EXPLORAÇÃO','Locais da investigação','Escolhe uma área. Podes regressar a qualquer momento.')+tpl('locations_grid',CARDS=cards)
    im,desc=SCENES[scene]
    elements=[]
    for eid,e in c['evidence'].items():
        if e['location'] != scene:continue
        found=eid in s['found'];challenge=eid in PUZZLES.get(c['id'],{})
        elements.append(f'<a href="/?view=inspect&scene={quote(scene)}&eid={eid}" '
                        f'class="hotspot {"is-found" if found else ""}">'
                        f'<span class="hotspot-symbol">{"✓" if found else "⌕"}</span><span>'
                        f'<strong>{E(e["object"])}</strong><small>'
                        f'{"Prova adicionada ao dossier" if found else "Analisar documento ou objeto"+(" · desafio" if challenge else "")}'
                        f'</small></span><span class="chevron">›</span></a>')
    return (page_head('INVESTIGAÇÃO / LOCAIS',scene,desc,
                      link('/?view=locations','Todos os locais','btn btn-mini btn-muted','←'))
            +tpl('location_detail',IMAGE=asset(im),CASE_ID=E(c['id']),
                 NUM_OBJECTS=len(elements),OBJECTS=''.join(elements)))


def render_inspect(s,scene,eid):
    c=current_case(s)
    if not c:return render_start_case(s)
    e=c['evidence'].get(eid)
    if e is None or e['location']!=scene:return render_locations(s,scene)
    is_found=eid in s['found'];challenge=PUZZLES.get(c['id'],{}).get(eid)
    if is_found:
        action='<div class="success-inline">✓ Esta informação já está guardada no teu dossier.</div>'+link('/?view=evidence','Abrir dossier','btn btn-outline')
    elif challenge:
        choices=''.join(f'<label class="choice"><input type="radio" name="choice" value="{i}" required><span class="choice-marker">{chr(65+i)}</span><span>{E(text)}</span></label>' for i,text in enumerate(challenge['choices']))
        action=(f'<div class="investigate-challenge"><div class="tiny-label">DESAFIO DE ANÁLISE</div>'
                f'<h3>{E(challenge["question"])}</h3>'
                '<p class="muted">Analisa os dados antes de escolher. Se acertares, a prova entra no dossier.</p>'
                '<form method="post" action="/action"><input type="hidden" name="action" value="solve_puzzle">'
                f'<input type="hidden" name="id" value="{E(eid)}"><div class="choice-stack">{choices}</div>'
                '<button class="btn btn-gold" type="submit">Confirmar análise →</button></form></div>')
    else:
        action='<div class="document-observation">Examinaste o documento. Regista-o no dossier para o consultar mais tarde.</div>'+btn('collect','Guardar no dossier',id=eid,cls='btn btn-gold',icon='▤')
    return (page_head('ANÁLISE DE OBJETO',e['object'],f'{scene} · Caso {c["id"]}',
                      link('/?view=locations&scene='+quote(scene),'Regressar ao local','btn btn-mini btn-muted','←'))
            +tpl('inspect',IMAGE=asset(img_for_evidence(e)),CATEGORY=E('PROVA PRINCIPAL' if eid.startswith('P') else 'PISTA SECUNDÁRIA'),
                 EID=E(eid),TITLE=E(e['title']),DESCRIPTION=E(e['text']),ACTION=action))


def render_interrogate(s,suspect_name=''):
    c=current_case(s)
    if not c:return render_start_case(s)
    available={p[0]:p for p in c['suspects']}
    if suspect_name in available and suspect_name!=s['selected_suspect']:
        s['selected_suspect']=suspect_name;s['speaker']=suspect_name;s['dialogue']=available[suspect_name][2]
    subject=s['selected_suspect']
    if subject not in available:
        subject=next(iter(available));s['selected_suspect']=subject
    name,role,initial=available[subject]
    tabs=''.join(f'<a href="/?view=interrogate&suspect={quote(p[0])}" class="suspect-tab {"selected" if p[0]==subject else ""}"><img src="{asset(PEOPLE_IMAGES[p[0]])}" alt=""><span>{E(p[0].split()[0])}</span></a>' for p in c['suspects'])
    dialogues=[('Onde estavas e o que sabes do incidente?','0','◷'),('Qual é a tua ligação ao caso?','1','♧'),('Há alguma informação que não contaste?','2','◇')]
    questions=''.join(btn('ask_question',title,id=idx,cls='question-button',icon=icon) for title,idx,icon in dialogues)
    found=sorted(s['found'],key=lambda v:(v[0],int(v[1:])))
    tray=''
    for eid in found:
        e=c['evidence'][eid]
        tray+=(f'<label class="tray-card"><input type="radio" name="evidence" value="{E(eid)}" required>'
               f'<span class="tray-visual"><img src="{asset(img_for_evidence(e))}" alt="">'
               f'<span class="tray-check">✓</span></span><strong>{E(e["title"])}</strong>'
               f'<small>{E(e["object"])}</small></label>')
    if not found:tray='<div class="tray-empty">Ainda não tens provas no dossier. Visita os locais para encontrar documentos e objetos.</div>'
    return (page_head('INTERROGATÓRIO / DETETIVE X','Interrogar suspeito',
                      f'Caso {c["id"]}: {c["title"]}',
                      f'<div class="top-suspect">Estás a interrogar: <strong>{E(name)}</strong></div>')
            +tpl('interrogate',TABS=tabs,PORTRAIT=asset(PEOPLE_IMAGES[name]),NAME=E(name),ROLE=E(role),CASE_ID=E(c['id']),
                 INITIAL=E(initial),SPEAKER=E(s['speaker'] or name),DIALOGUE=E(s['dialogue'] or initial),
                 QUESTIONS=questions,COUNT=len(found),TRAY=tray,DISABLED='disabled' if not found else ''))


def render_evidence(s):
    c=current_case(s)
    if not c:return render_start_case(s)
    found=sorted(s['found'],key=lambda x:(x[0],int(x[1:])))
    n,sc=summary_counts(s)
    cards=''
    for eid in found:
        e=c['evidence'][eid]
        cards+=(f'<div class="evidence-card"><img src="{asset(img_for_evidence(e))}" alt="">'
                f'<div class="evidence-card-body"><div class="tiny-label">{E(eid)} · {E(e["location"])}</div>'
                f'<h3>{E(e["title"])}</h3><p>{E(e["text"])}</p></div></div>')
    if not cards:cards='<div class="no-evidence">Ainda não há provas. Explora os locais e analisa objetos para preencher o dossier.</div>'
    selects=''.join(f'<option value="{E(eid)}">{E(eid)} — {E(c["evidence"][eid]["title"])}</option>' for eid in found)
    deductions=''.join(f'<div class="deduction-row">✓ Ligação confirmada entre {E(a)} e {E(b)}.</div>' for a,b in sorted(s['deductions'])) or '<p class="muted">Ainda não registaste nenhuma ligação entre provas.</p>'
    form=(f'<form method="post" action="/action" class="deduction-form">'
          f'<input type="hidden" name="action" value="deduce">'
          f'<label>Primeira prova<select name="proof1" required><option value="">Seleciona</option>{selects}</select></label>'
          f'<label>Segunda prova<select name="proof2" required><option value="">Seleciona</option>{selects}</select></label>'
          '<button class="btn btn-gold" type="submit">Testar ligação</button></form>'
          if len(found)>=2 else '<p class="muted">Encontra pelo menos duas provas para começares a relacionar informações.</p>')
    return (page_head('DOSSIER DE PROVAS','Quadro de provas',f'{n}/6 provas principais · {sc}/2 pistas secundárias. Seleciona e relaciona os factos.')
            +tpl('evidence',COUNT=len(found),CARDS=cards,FORM=form,DEDUCTIONS=deductions))


def render_notes(s):
    c=current_case(s)
    if not c:return render_start_case(s)
    checklist=[('Recolher 4 provas principais',sum(x.startswith('P') for x in s['found'])>=4),
               ('Descobrir um par de provas consistente',any(set(pair) <= s['found'] for pair in c['valid_pairs'])),
               ('Fazer pelo menos um confronto',bool(s['confronted'])),
               ('Apresentar a acusação final',bool(s['result']))]
    tasks=''.join(f'<div class="task-line"><span class="task-check {"yes" if done else ""}">{"✓" if done else ""}</span><span>{E(title)}</span></div>' for title,done in checklist)
    asked=''.join(f'<div class="answer-brief">{E(p)}</div>' for p in sorted(s['asked'])) or '<p class="muted">Ainda não fizeste perguntas.</p>'
    return page_head('BLOCO DE NOTAS','Notas do detetive','Escreve hipóteses e acompanha o progresso.')+tpl('notes',NOTES=E(s['notes']),TASKS=tasks,ASKED=asked)


def render_accuse(s):
    c=current_case(s)
    if not c:return render_start_case(s)
    n,_=summary_counts(s)
    if s['result']:
        result=s['result']
        return (page_head('CASO ENCERRADO','Relatório final',f'{c["id"]} · {c["title"]}')
                +tpl('accuse_solved',RANK=E(result['rank']),SCORE=result['score'],CONCLUSION=E(c['conclusion'])))
    if not can_accuse(s):
        pair_found=any(set(x)<=s['found'] for x in c['valid_pairs'])
        return (page_head('RELATÓRIO OFICIAL','Acusação final','Ainda não reuniste todas as condições para entregar uma acusação.')
                +tpl('accuse_locked',PROOF_CLASS='fulfilled' if n>=4 else '',PROOF_MARK='✓' if n>=4 else '○',
                     COUNT=n,PAIR_CLASS='fulfilled' if pair_found else '',PAIR_STATUS='sim' if pair_found else 'a investigar'))
    suspects=''.join(f'<option value="{E(p[0])}">{E(p[0])}</option>' for p in c['suspects'])
    motives=''.join(f'<option value="{E(x)}">{E(x)}</option>' for x in s['motive_order'])
    proofs=''.join(f'<option value="{E(eid)}">{E(eid)} — {E(c["evidence"][eid]["title"])}</option>' for eid in sorted(s['found']))
    return (page_head('RELATÓRIO OFICIAL','Acusação final','Indica o suspeito, o motivo e duas provas distintas para sustentar a tua conclusão.')
            +tpl('accuse_form',CASE_ID=E(c['id']),SUSPECTS=suspects,MOTIVES=motives,PROOFS=proofs))


# ## JOGO 2 — Sala de Interrogatório
def render_quiz(s):
    questions=s['quiz']
    if not questions:
        return page_head('JOGO 02','Sala de Interrogatório','Trinta situações disponíveis, oito escolhidas em cada partida.')+tpl('quiz_intro')
    i=s['quiz_index']
    if i>=len(questions):
        details=''.join(f'<div class="quiz-result-item"><span>Ronda {j+1} · Pergunta {x["id"]}</span><strong>+{x["score"]} pontos</strong></div>' for j,x in enumerate(s['quiz_results']))
        return page_head('SALA DE INTERROGATÓRIO','Interrogatório concluído','Terminaste as oito rondas.')+tpl('quiz_results',SCORE=s['quiz_score'],RESULTS=details)
    q=questions[i]
    level={'Fácil':'easy','Média':'medium','Difícil':'hard'}[q['level']]
    header=page_head(f'SALA DE INTERROGATÓRIO · RONDA {i+1}/8',q['title'],
                     'Analisa os factos antes de responder.',f'<span class="difficulty {level}">{E(q["level"])}</span>')
    if s['quiz_witness'] is None:
        buttons=''.join(btn('quiz_witness',q[opt],id=opt,cls='witness-choice',icon=opt) for opt in 'ABC')
        step=f'<h3>Qual dos depoimentos entra em contradição?</h3><div class="question-stack">{buttons}</div>'
    elif s['quiz_proof'] is None:
        selected=s['quiz_witness']
        buttons=''.join(btn('quiz_proof',proof,id=str(j),cls='witness-choice',icon=str(j+1)) for j,proof in enumerate(q['proofs']))
        step=(f'<div class="selected-answer">Depoimento selecionado: <b>{E(selected)}</b> — {E(q[selected])}</div>'
              f'<h3>Qual é a prova que justifica a tua escolha?</h3><div class="question-stack">{buttons}</div>')
    else:
        gain=s['quiz_results'][-1]['score']
        step=(f'<div class="quiz-feedback"><h3>Ronda analisada · +{gain} pontos</h3>'
              f'<p><b>Depoimento inconsistente:</b> {E(q["answer"])} — {E(q[q["answer"]])}</p>'
              f'<p><b>Prova:</b> {E(q["proofs"][q["correct_proof"]])}</p><p>{E(q["explanation"])}</p></div>'
              +btn('quiz_next','Ver resultados' if i==7 else 'Próxima ronda →',cls='btn btn-gold btn-large'))
    dots=''.join(f'<span class="round-dot {"done" if n<i else ""} {"now" if n==i else ""}"></span>' for n in range(8))
    return header+tpl('quiz_play',DOTS=dots,FACT=E(q['fact']),SCORE=s['quiz_score'],STEP=step)


# ## JOGO 3 — O Cofre Trancado
def render_safe(s):
    level=s['safe_level'];limit=SAFE_LIMITS[level];trials=s['safe_guesses']
    won=s['safe_won'];lost=len(trials)>=limit and not won
    message='COFRE DESBLOQUEADO' if won else 'TENTATIVAS ESGOTADAS' if lost else 'SISTEMA DE SEGURANÇA ATIVO'
    status=f'<div class="safe-confirm">{message}</div>' if won or lost else '<div class="safe-status">Introduz três algarismos para desbloquear.</div>'
    code=f'{s["safe_code"]:03d}' if won or lost else '•••'
    history=''.join(f'<div class="try-item"><span>{x["guess"]:03d}</span><strong>{E(x["hint"])}</strong></div>' for x in reversed(trials[-8:])) or '<p class="muted">Ainda não introduziste códigos.</p>'
    levels=''.join(btn('set_safe_level',label,id=k,cls=f'level-pill {"active" if level==k else ""}') for k,label in [('facil','Fácil · 16'),('medio','Médio · 12'),('dificil','Difícil · 8')])
    form=(f'<form method="post" action="/action" class="safe-guess-form"><input type="hidden" name="action" value="safe_guess">'
          '<label for="safe-input">A TUA COMBINAÇÃO</label><input id="safe-input" name="guess" inputmode="numeric" autocomplete="off" '
          'minlength="3" maxlength="3" pattern="[0-9]{3}" placeholder="000" autofocus required>'
          '<button class="btn btn-gold" type="submit">Verificar código</button></form>'
          if not won and not lost else f'<div class="revealed-code">Código correto: <b>{s["safe_code"]:03d}</b></div>')
    return (page_head('JOGO 03','O Cofre Trancado','Um código aleatório de três algarismos. Segue as pistas para abrir o cofre.')
            +tpl('safe',COUNT=len(trials),LIMIT=limit,LEVELS=levels,CODE=code,STATUS_TEXT=E(message),STATUS=status,FORM=form,HISTORY=history))


def render_page(s,view,params):
    c=current_case(s)
    if view in ('case','suspects','locations','inspect','interrogate','evidence','notes','accuse') and not c and view!='case':
        view='case'
    screen={
        'home':lambda:render_home(s),'case':lambda:render_case(s),'suspects':lambda:render_suspects(s),
        'locations':lambda:render_locations(s,params.get('scene','')),
        'inspect':lambda:render_inspect(s,params.get('scene',''),params.get('eid','')),
        'interrogate':lambda:render_interrogate(s,params.get('suspect','')),
        'evidence':lambda:render_evidence(s),'notes':lambda:render_notes(s),
        'accuse':lambda:render_accuse(s),'quiz':lambda:render_quiz(s),
        'safe':lambda:render_safe(s),
    }.get(view,lambda:render_home(s))()
    flash=''
    if s['flash']:
        flash=(f'<div class="flash {E(s["flash_kind"])}" role="alert">'
               f'<span>{"✓" if s["flash_kind"]=="success" else "!"}</span>{E(s["flash"])}</div>')
        s['flash']=''
    main_count,_=summary_counts(s)
    detective_views={'case','suspects','locations','inspect','interrogate','evidence','notes','accuse'}
    if view in detective_views and c:
        progress=round(main_count/6*100)
        progress_label=f'PROGRESSO DO CASO: {progress}%'
        badge=f'<span class="case-badge">DOSSIER {E(c["id"])} · {E(c["genre"])}</span>'
        badge+=f'<div class="score-indicator">PONTUAÇÃO: {max(0,100-s["penalty"])}/100</div>'
    elif view=='quiz':
        progress=round(min(s['quiz_index'],8)*100/8) if s['quiz'] else 0
        progress_label=f'SALA DE INTERROGATÓRIO · {min(s["quiz_index"],8)}/8 RONDAS'
        badge='<span class="case-badge">JOGO 02</span>'
    elif view=='safe':
        limit=SAFE_LIMITS[s['safe_level']]
        progress=round(len(s['safe_guesses'])*100/limit)
        progress_label=f'COFRE · {len(s["safe_guesses"])}/{limit} TENTATIVAS'
        badge='<span class="case-badge">JOGO 03</span>'
    else:
        progress=0;progress_label='3 JOGOS DISPONÍVEIS'
        badge='<span class="case-badge">BLACKWOOD POLICE DEPARTMENT</span>'
    bar=(f'<div class="case-status">{badge}<div class="progress-caption">{E(progress_label)}</div>'
         f'<div class="progress-meter"><i style="width:{progress}%"></i></div></div>')
    active='case' if view in detective_views else view
    result=BASE_TEMPLATE
    result=re.sub(r'<!-- BARRA_CASO_INICIO -->.*?<!-- BARRA_CASO_FIM -->',lambda match:bar,result,flags=re.S)
    result=re.sub(r'<!-- ECRA_INICIO -->.*?<!-- ECRA_FIM -->',lambda match:screen,result,flags=re.S)
    result=result.replace('<!-- MENSAGEM_DO_PYTHON -->',flash)
    result=result.replace('<!-- MENU_INTERNO_DETETIVE -->',detective_subnav(s,view) if view in detective_views else '')
    result=re.sub(r'<template id="view-[a-z_]+">.*?</template>', '', result, flags=re.S)
    # O HTML inclui as quatro entradas principais do menu; o Python só assinala a ativa.
    result=result.replace('class="side-item active" data-section="home"','class="side-item" data-section="home"')
    result=result.replace(f'class="side-item" data-section="{active}"',f'class="side-item active" data-section="{active}"')
    return result.encode('utf-8')


def process_action(s, params):
    action=params.get('action','')
    value=params.get('id','')
    c=current_case(s)
    dest='/'

    if action=='new_case':
        new_case(s)
        return '/?view=case'

    if action=='collect' and c and value in c['evidence']:
        if value not in PUZZLES.get(c['id'],{}):
            s['found'].add(value)
            notify(s,f"Prova recolhida: {c['evidence'][value]['title']}",'success')
        return f'/?view=inspect&scene={quote(c["evidence"][value]["location"])}&eid={quote(value)}'

    if action=='solve_puzzle' and c and value in c['evidence']:
        challenge=PUZZLES.get(c['id'],{}).get(value)
        if challenge:
            try: choice=int(params.get('choice','-1'))
            except ValueError: choice=-1
            if choice==challenge['correct']:
                s['found'].add(value);s['solved_puzzles'].add(value)
                notify(s,challenge['explanation']+' · Prova adicionada ao dossier.','success')
            else:
                s['penalty']+=2
                notify(s,'Essa interpretação não corresponde aos registos. Volta a analisar os dados. −2 pontos.','error')
        return f'/?view=inspect&scene={quote(c["evidence"][value]["location"])}&eid={quote(value)}'

    if action=='ask_question' and c:
        name=s['selected_suspect']
        info=next((p for p in c['suspects'] if p[0]==name),None)
        if info:
            if value=='0': reply=info[2]
            elif value=='1': reply=f"Trabalho como {info[1].lower()}. Conheço pessoas ligadas a este caso, mas isso não prova nada contra mim."
            else: reply="Já te contei a minha versão. Se encontraste algo que a contradiz, mostra-me a prova e falamos sobre isso."
            s['speaker']=name;s['dialogue']=reply
            s['asked'].add(f'{name}: pergunta {int(value)+1}' if value in ('0','1','2') else name)
        return f'/?view=interrogate&suspect={quote(name)}'

    if action=='confront' and c:
        name=params.get('suspect','');eid=params.get('evidence','')
        if name not in [p[0] for p in c['suspects']]:
            return '/?view=interrogate'
        s['selected_suspect']=name
        if eid not in s['found']:
            notify(s,'Seleciona uma prova que tenhas encontrado.','error')
        else:
            match=next((x for x in c['confrontations'] if x[0]==name and x[1]==eid),None)
            if match:
                s['speaker']=name;s['dialogue']=match[3]
                s['confronted'].add((name,eid))
                notify(s,'Confronto realizado. A nova declaração fica registada na tua investigação.','success')
            else:
                s['speaker']=name
                s['dialogue']='Essa prova não contradiz diretamente o que te disse. Mostra-me algo relevante para o meu depoimento.'
                notify(s,'Essa prova não permite um confronto conclusivo com este suspeito.','info')
        return f'/?view=interrogate&suspect={quote(name)}'

    if action=='deduce' and c:
        a,b=params.get('proof1',''),params.get('proof2','')
        if a==b or a not in s['found'] or b not in s['found']:
            notify(s,'Seleciona duas provas diferentes que pertençam ao teu dossier.','error')
        elif qualified_pair(c,a,b):
            s['deductions'].add(tuple(sorted((a,b))))
            notify(s,'Boa dedução! Estas duas provas formam uma ligação consistente.','success')
        else:
            pair=tuple(sorted((a,b)))
            if pair in s['wrong_deductions']:
                notify(s,'Já tinhas testado esta combinação. Não voltas a perder pontos por este par.','info')
            else:
                s['wrong_deductions'].add(pair)
                s['penalty']+=2
                notify(s,'Esta ligação não é sustentada pelas provas. −2 pontos.','error')
        return '/?view=evidence'

    if action=='save_notes' and c:
        s['notes']=params.get('notes','')[:4000]
        notify(s,'Notas guardadas durante esta partida.','success')
        return '/?view=notes'

    if action=='accuse' and c:
        if not can_accuse(s):
            notify(s,'A acusação ainda não está desbloqueada.','error')
        else:
            person,motive,a,b=(params.get(k,'') for k in ('suspect','motive','proof1','proof2'))
            if not all((person,motive,a,b)) or a==b or a not in s['found'] or b not in s['found']:
                notify(s,'Preenche todos os campos e escolhe duas provas diferentes do dossier.','error')
            elif person==c['culprit'] and motive==c['motive'] and qualified_pair(c,a,b):
                score=max(0,100-s['penalty'])
                rank='MASTER DETECTIVE' if score>=90 else 'SENIOR INVESTIGATOR' if score>=70 else 'JUNIOR DETECTIVE'
                s['result']={'score':score,'rank':rank}
                notify(s,'Investigação concluída. Excelente trabalho!','success')
            else:
                s['penalty']+=15;s['wrong_accusations']+=1
                notify(s,'Acusação não comprovada. Revê o responsável, o motivo ou as duas provas. −15 pontos.','error')
        return '/?view=accuse'

    if action=='start_quiz':
        s.update(quiz=draw_questions(),quiz_index=0,quiz_witness=None,
                 quiz_proof=None,quiz_score=0,quiz_results=[])
        notify(s,'Interrogatório iniciado. Escolhe um depoimento e a respetiva prova.','success')
        return '/?view=quiz'

    if action=='quiz_witness' and s['quiz'] and s['quiz_index']<8:
        if s['quiz_witness'] is None and value in ('A','B','C'):
            s['quiz_witness']=value
        return '/?view=quiz'

    if action=='quiz_proof' and s['quiz'] and s['quiz_index']<8:
        if s['quiz_witness'] and s['quiz_proof'] is None and value in ('0','1','2'):
            q=s['quiz'][s['quiz_index']];n=int(value)
            got=(6 if s['quiz_witness']==q['answer'] else 0)+(4 if n==q['correct_proof'] else 0)
            s['quiz_proof']=n;s['quiz_score']+=got
            s['quiz_results'].append({'id':q['id'],'score':got})
        return '/?view=quiz'

    if action=='quiz_next':
        if s['quiz_proof'] is not None:
            s['quiz_index']+=1;s['quiz_witness']=None;s['quiz_proof']=None
        return '/?view=quiz'

    if action in ('set_safe_level','reset_safe'):
        newlevel=value if action=='set_safe_level' and value in SAFE_LIMITS else s['safe_level']
        s.update(safe_level=newlevel,safe_code=random.randint(0,999),safe_guesses=[],safe_won=False)
        return '/?view=safe'

    if action=='safe_guess':
        val=params.get('guess','').strip()
        if s['safe_won'] or len(s['safe_guesses'])>=SAFE_LIMITS[s['safe_level']]:
            notify(s,'A partida terminou. Começa outra para continuar.','info')
        elif len(val)!=3 or not val.isascii() or not val.isdigit():
            notify(s,'Introduz exatamente três algarismos, por exemplo 042.','error')
        else:
            guess=int(val)
            if any(g['guess']==guess for g in s['safe_guesses']):
                notify(s,'Já tentaste esse código. Escolhe outro.','error')
            else:
                code=s['safe_code']
                hint='CÓDIGO CERTO ✓' if guess==code else ('O CÓDIGO É MAIOR ↑' if guess<code else 'O CÓDIGO É MENOR ↓')
                s['safe_guesses'].append({'guess':guess,'hint':hint})
                s['safe_won']=guess==code
                if guess==code:notify(s,'Conseguiste abrir o cofre!','success')
                elif len(s['safe_guesses'])>=SAFE_LIMITS[s['safe_level']]:
                    notify(s,f'Tentativas esgotadas. O código era {code:03d}.','error')
                else:notify(s,hint,'info')
        return '/?view=safe'

    return '/'


class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if os.environ.get('VERBOSE')=='1':super().log_message(format,*args)

    def get_session(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except Exception:pass
        sid=cookie['bw_session'].value if 'bw_session' in cookie else ''
        with SESSIONS_LOCK:
            if sid not in SESSIONS:
                sid=secrets.token_urlsafe(24)
                SESSIONS[sid]=new_state()
                self._new_session_cookie=f'bw_session={sid}; Path=/; HttpOnly; SameSite=Lax'
            else:self._new_session_cookie=None
            state=SESSIONS[sid]
        return state

    def respond(self,code,content,typ='text/html; charset=utf-8',extra=None):
        self.send_response(code)
        self.send_header('Content-Type',typ)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store' if typ.startswith('text/html') else 'public, max-age=3600')
        if getattr(self,'_new_session_cookie',None):self.send_header('Set-Cookie',self._new_session_cookie)
        if extra:
            for k,v in extra.items():self.send_header(k,v)
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        self._new_session_cookie=None
        url=urlparse(self.path)
        if url.path=='/style.css':
            path=ROOT/'style.css'
            return self.respond(200,path.read_bytes(),'text/css; charset=utf-8')
        if url.path.startswith('/assets/'):
            basename=url.path.rsplit('/',1)[-1]
            path=ROOT/'assets'/basename
            if '/' in basename or '..' in basename or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp') or not path.is_file():
                return self.respond(404,b'Not Found','text/plain; charset=utf-8')
            return self.respond(200,path.read_bytes(),'image/jpeg' if path.suffix.lower()=='.jpg' else 'image/png')
        if url.path=='/health':return self.respond(200,b'OK','text/plain; charset=utf-8')
        if url.path!='/':return self.respond(404,b'Not Found','text/plain; charset=utf-8')
        s=self.get_session()
        params={k:v[0] for k,v in parse_qs(url.query,keep_blank_values=True).items()}
        view=params.get('view','home')
        try:
            content=render_page(s,view,params)
            return self.respond(200,content)
        except Exception as exc:
            import traceback;traceback.print_exc()
            return self.respond(500,('Erro de interface: '+E(str(exc))).encode('utf-8'))

    def do_POST(self):
        self._new_session_cookie=None
        if urlparse(self.path).path!='/action':
            return self.respond(404,b'Not Found','text/plain; charset=utf-8')
        try:
            count=int(self.headers.get('Content-Length','0'))
        except ValueError:count=0
        if count>40000 or count<=0:
            return self.respond(413,b'Invalid request','text/plain; charset=utf-8')
        body=self.rfile.read(count).decode('utf-8','replace')
        params={k:v[0] for k,v in parse_qs(body,keep_blank_values=True).items()}
        s=self.get_session()
        try:
            destination=process_action(s,params)
        except Exception as exc:
            import traceback;traceback.print_exc()
            notify(s,'Foi encontrado um erro ao processar esta ação. Podes continuar a jogar.','error')
            destination='/'
        self.send_response(303)
        self.send_header('Location',destination)
        self.send_header('Cache-Control','no-store')
        if getattr(self,'_new_session_cookie',None):self.send_header('Set-Cookie',self._new_session_cookie)
        self.send_header('Content-Length','0')
        self.end_headers()


def run_server():
    port=int(os.environ.get('PORT','8765'))
    host='0.0.0.0' if os.environ.get('PORT') else '127.0.0.1'
    try:server=ThreadingHTTPServer((host,port),WebHandler)
    except OSError:
        if os.environ.get('PORT'):raise
        server=ThreadingHTTPServer((host,0),WebHandler)
        port=server.server_port
    url=f'http://127.0.0.1:{port}'
    print('\n'+'═'*54+'\n THE BLACKWOOD FILES — JOGO PRONTO\n'+'═'*54)
    print(' Abre no navegador: '+url)
    print(' Para encerrar: Ctrl+C no Terminal\n')
    if os.environ.get('NO_BROWSER')!='1':
        threading.Timer(0.65,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nA encerrar o jogo...')
    finally:server.server_close()


if __name__=='__main__':run_server()
