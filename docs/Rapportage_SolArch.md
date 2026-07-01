# **Rapportage Solution Architecture**

###### *Mikail Sari, Dymo Waltheer, Eren Aygun & Stef Rensma*

# Microservices based on the principles of DDD

De microservices worden direct aangemaakt in de root folder van het project.
Deze geïsoleerde services functioneren als één Bounded Context.
Deze BC’s halen we uit de Context Map die we hebben gemaakt doot te kijken naar de casus.

Binnen de service kun je routeren naar de “app/” map waar onze “models.py” te vinden is.
Binnen deze file zijn de DDD-patronen gedefinieerd, zoals de aggregrate root en mogelijke Value Objects,
bijvoorbeeld enige ordergegevens of klantengegevens die specifiek aan een order gekoppeld zijn.
Onze microservice verbindt met de database via onze “database.py” file.
Via deze file heeft de microservice een eigen database connectie,
wat betekent dat het alleen binnen deze service de data beheert en niet haar eigen tabellen/data deelt met andere microservices.

Door de orderlogica te isoleren specifiek in zo een microservice en DDD principes er op toe te passen,
voorkom je dat wijzigingen in klantenservice en of warehouseservice invloed hebben op orderprocessen.
Dit verhoogt niet alleen de onderhoudbaarheid, maar zorgt er ook voor dat het ontwikkelteam van order-management onafhankelijk van anderen wijzigingen kan uitvoeren.

# Eventual Consistency

Dit proces start in "main.py", waar de endpoints in staan gedefinieerd.
Wanneer een klant een POST request uitvoert, wordt de inkomende data gevalideerd via "models.py".
Als de validatie slaagt, wordt er in "main.py" een unieke id gegenereerd
en wordt de data opgeslagen via de SQLAlchemy sessie vanuit "database.py".
Daarnaast wordt er in "messaging.py" een domain event aangemaakt en gepubliceerd.
Deze event wordt vervolgens ontvangen door andere services via hun "consumer.py" bestanden.
En tot slot stuurt "main.py" een HTTP-response terug naar de gebruiker met de opgeslagen data en een statuscode.


# EDA (Event Driven Architecture) based on messaging

EDA bevindt zich in 2 specifieke bestanden: "messaging.py" en "consumer.py".
In "messaging.py" bevindt zich de logica om de verbinding te maken met de message broker (in dit geval RabbitMQ)
en om events te publiceren, zoals een OrderCreated of OrderCancelled.
Het bestand "consumer.py" is in dit geval de listener van deze service.
Deze draait op de achtergrond om binnenkomende requests van andere microservices op te vangen, die vervolgens in de database worden verwerkt.

EDA is toegepast zodat order-management niet direct hoeft te laten weten welke andere services bestaan of op dat moment online runnen.
Als de payment service tijdelijk niet online is, plaatst de message broker de request in de wachtrij.
Zodra deze service weer online komt te staan, wordt de request alsnog verwerkt zonder dat er data verloren gaat.

# CQRS (Command Query Responsibility Segregation)

CQRS is het scheiden van verantwoordelijkheid van de Commands & Queries op een data model,
we passen dit toe bij de order-management. De commands: POST, PUT, DELETE worden eerst verstuurd naar een event store waar het als een event wordt opgeslagen. Hiermee kan je
gemakkelijker de geschiedenis bijhouden van orders. Vervolgens wordt het de RabbitMQ bus opgezet en opgepakt door een Consumer die het kan denormalizeren en in de "order_view" tabel zet.
De "order_view" tabel is voor het lezen van de order data. Dit is voor betere performance. Wij hebben gekozen dit toe te passen bij de Order Service, omdat je veel order gegevens wilt
bekijken, aanpassen en aanmaken. Dit maakt het ook makkelijk bij te houden wat er met een order gebeurt, een order gaat natuurlijk door een warehouse, delivering service, en dit moet je
allemaal bij kunnen houden.

# Event Sourcing

Opvolgend op CQRS hebben wij, zoals te lezen was, event sourcing toegepast bij de Order Service.
Event sourcing bevindt zich tussen de interactie van "database.py" en "models.py".
In plaats van dat een update request in de database simpelweg de status van een order overschrijft van bijvoorbeeld
"In behandeling" naar "Processed", worden de events opgeslagen in een tabel in PostgreSQL, met de tijd en alle benodigde data.
Wij passen dus ook nooit een event aan, als je de status wijzigt maakt hij een nieuw event aan en update hij de "order_view" tabel zodat alles consistent blijft.

# Enterprise Integration Patterns

Enterprise Integration Patterns worden op dit project toegepast door middel van RabbitMQ als centrale message bus.
Alle microservices van dit project communiceren niet direct met elkaar, maar via gepubliceerde events.
Andere services ontvangen deze events door middel van hun eigen "consumer.py" bestanden en verwerken deze om hun eigen models of database bij te werken, zodat er geen directe koppeling hoeft te zijn tussen de services en ze dus onafhankelijk van elkaar blijven.
Dit zorgt dus voor communicatie tussen de services en helpt in de schaalbaarheid van het project, omdat elke service alleen reageert op events die relevant zijn voor hun eigen domein.

# Containerization of your implementation

Het project is gecontaineriseerd met Docker met gebruik van docker compose. Elke microservice / API leeft in een eigen container. Dit zijn vooral Python FastAPI services, met een enkele NodeJS service, deze combinatie van talen laat de voordelen van containerisatie zien. Elke API container heeft ook een eigen consumer container die op de achtergrondevents van RabbitMQ consumeert en verwerkt.

Naast API services zijn er ook 2 gedeelde containers, RabbitMQ en PostgresDB. Deze worden gebruikt voor het opstellen van een EDA (Event Driven Architecture) met gebruik van messaging en het opslaan van event data.
