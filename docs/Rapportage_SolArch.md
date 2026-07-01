# **Rapportage Solution Architecture**

###### *Mikail Sari, Dymo Waltheer, Eren Aygun & Stef Rensma*

# Microservices based on the principles of DDD
De microservices worden direct aangemaakt in de root folder van de project. Deze geisoleerde functies functioneert als een specifieke Bounded Context. Deze BC’s halen we uit de Context Map waarbij we hebben gekeken naar de casus en de BC’s vanuit daar hebben geidentificeert. Binnen de service kun je routeren naar de “app/” map waar onze “models.py” te vinden is. Binnen deze file zijn de DDD-patronen gedefinieerd, zoals de aggregrate root en mogelijke Value Objects, bijvoorbeeld enige ordergegevens of klantengegevens die specifiek aan een order gekoppeld zijn. Onze microservice verbindt met de database via onze “database.py” file. Via deze file heeft de microservice een eigen database connectie, wat betekent dat het alleen binnen deze service de data beheert en niet haar eigen tabellen/data deelt met andere microservices.  Door de orderlogica te isoleren specifiek in zo een microservice en DDD principes er op toe te passen, voorkom je dat wijzigingen in klantenservice en of warehouseservice invloed hebben op ordersprocessen. Dit verhoogt niet alleen de onderhoudbaarheid, maar zorgt er ook voor dat het ontwikkelteam van order-management wijzigingen kan uitvoeren onafhankelijk van anderen.

Door de orderlogica te isoleren specifiek in zo een microservice en DDD principes er op toe te passen, voorkom je dat wijzigingen in klantenservice en of warehouseservice invloed hebben op ordersprocessen. Dit verhoogt niet alleen de onderhoudbaarheid, maar zorgt er ook voor dat het ontwikkelteam van order-management wijzigingen kan uitvoeren onafhankelijk van anderen.


# Eventual Consistency


# EDA (Event Driven Architecture) based on messaging


# CQRS (Command Query Responsibility Segregation)


# Event Sourcing


# Enterprise Integration Patterns


# Containerization of your implementation

