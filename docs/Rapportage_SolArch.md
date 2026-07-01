# **Rapportage Solution Architecture**

###### *Mikail Sari, Dymo Waltheer, Eren Aygun & Stef Rensma*

# Microservices based on the principles of DDD
De microservices worden direct aangemaakt in de root folder van de project. Deze geisoleerde functies functioneert als een specifieke Bounded Context. Deze BC’s halen we uit de Context Map waarbij we hebben gekeken naar de casus en de BC’s vanuit daar hebben geidentificeert. Binnen de service kun je routeren naar de “app/” map waar onze “models.py” te vinden is. Binnen deze file zijn de DDD-patronen gedefinieerd, zoals de aggregrate root en mogelijke Value Objects, bijvoorbeeld enige ordergegevens of klantengegevens die specifiek aan een order gekoppeld zijn. Onze microservice verbindt met de database via onze “database.py” file. Via deze file heeft de microservice een eigen database connectie, wat betekent dat het alleen binnen deze service de data beheert en niet haar eigen tabellen/data deelt met andere microservices.  Door de orderlogica te isoleren specifiek in zo een microservice en DDD principes er op toe te passen, voorkom je dat wijzigingen in klantenservice en of warehouseservice invloed hebben op ordersprocessen. Dit verhoogt niet alleen de onderhoudbaarheid, maar zorgt er ook voor dat het ontwikkelteam van order-management wijzigingen kan uitvoeren onafhankelijk van anderen.

Door de orderlogica te isoleren specifiek in zo een microservice en DDD principes er op toe te passen, voorkom je dat wijzigingen in klantenservice en of warehouseservice invloed hebben op ordersprocessen. Dit verhoogt niet alleen de onderhoudbaarheid, maar zorgt er ook voor dat het ontwikkelteam van order-management wijzigingen kan uitvoeren onafhankelijk van anderen.


# Eventual Consistency


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

# Enterprise Integration Patterns


# Containerization of your implementation
Het project is gecontaineriseerd met Docker met gebruik van docker compose. Elke microservice / API leeft in een eigen container. Dit zijn vooral Python FastAPI services, met een enkele NodeJS service, deze combinatie van talen laat de voordelen van containerisatie zien. Elke API container heeft ook een eigen consumer container die op de achtergrondevents van RabbitMQ consumeert en verwerkt.

Naast API services zijn er ook 2 gedeelde containers, RabbitMQ en PostgresDB. Deze worden gebruikt voor het opstellen van een EDA (Event Driven Architecture) met gebruik van messaging en het opslaan van event data.
