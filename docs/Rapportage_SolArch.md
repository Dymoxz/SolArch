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

Dit proces start in "Main.py". Wanneer een klant een bestelling plaatst via een POST Request, wordt eerst de inkomende data gevalideerd volgens de bijbehorende Pyndatic modellen. Hierbij wordt dus gecontroleerd of de verplichte velden aanwezig zijn en of de waarden voldoen aan de domeinregels van de service. Wanneer de validatie slaagt, wordt er een unieke identifier gegenereerd voor het nieuwe object en wordt er vervolgens met behulp van de database opgeslagen. Hier wordt SQLAlchemy verantwoordelijk gehouden voor het uitoeren van de persistente opslag. Daarnaast wordt er, afhankelijk van de type actie, een domein event aangemaakt en gepubliceerd naar RabbitMQ. Dit event zorgt ervoor dat andere services binnen het systeem op de hoogte gebracht worden van de wijzigingen en hun eigen read models kunnen updaten. Tot slot stuurt de API een HTTP-response terug naar de gebruiker met de aangemaakte of gewijzigde data en een passende statuscode. Hierdoor wordt de actie direct bevestigd, terwijl de verdere verwerkingen asynchroon en losgekoppeld in de achtergrond plaatsvindt.

# EDA (Event Driven Architecture) based on messaging

# CQRS (Command Query Responsibility Segregation)

CQRS is het scheiden van verantwoordelijkheid van de Commands & Queries op een data model,
we passen dit toe bij de order-management. De commands: POST, PUT, DELETE worden eerst verstuurd naar een event store waar het als een event wordt opgeslagen. Hiermee kan je
gemakkelijker de geschiedenis bijhouden van orders. Vervolgens wordt het de RabbitMQ bus opgezet en opgepakt door een Consumer die het kan denormalizeren en in de "order_view" tabel zet.
De "order_view" tabel is voor het lezen van de order data. Dit is voor betere performance. Wij hebben gekozen dit toe te passen bij de Order Service, omdat je veel order gegevens wilt
bekijken, aanpassen en aanmaken. Dit maakt het ook makkelijk bij te houden wat er met een order gebeurt, een order gaat natuurlijk door een warehouse, delivering service, en dit moet je
allemaal bij kunnen houden.

# Event Sourcing

Opvolgend op CQRS hebben wij, zoals te lezen was, event sourcing toegepast bij de Order Service. We slaan de events op in een tabel in PostgreSQL, met de tijd en alle benodigde data.
Wij passen dus ook nooit een event aan, als je de status wijzigt maakt hij een nieuw event aan en update hij de "order_view" tabel zodat alles consistent blijft.

Event sourcing bevindt zich tussen de interactie van "database.py" en "models.py".
In plaats van dat een update request in de database simpelweg de status van een order overschrijft van bijvoorbeeld
"In behandeling" naar "Processed", slaat "database.py" een nieuwe rij op in een event tabel.
Als een order moet worden geladen haalt "database.py" alle "past events" op voor dat specifieke order-id. Hierna wordt de huidige status weer chronologisch gereconstrueerd binnen de klassen in "models.py".

# Enterprise Integration Patterns



# Containerization of your implementation

Het project is gecontaineriseerd met Docker met gebruik van docker compose. Elke microservice / API leeft in een eigen container. Dit zijn vooral Python FastAPI services, met een enkele NodeJS service, deze combinatie van talen laat de voordelen van containerisatie zien. Elke API container heeft ook een eigen consumer container die op de achtergrondevents van RabbitMQ consumeert en verwerkt.

Naast API services zijn er ook 2 gedeelde containers, RabbitMQ en PostgresDB. Deze worden gebruikt voor het opstellen van een EDA (Event Driven Architecture) met gebruik van messaging en het opslaan van event data.
