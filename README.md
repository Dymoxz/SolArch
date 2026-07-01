nieuwe folder = microservice
Folder structure
/service-name
  /app
    main.py
    *andere python files?
  Dockerfile
  requirements.txt

zorg dat in docker-compose je nieuwe serrvice toe voeg. zoals:

  order-api:
    build: ./order-management
    container_name: ball_order_api
    ports:
      - "8000:8000"
    environment:
      # Verwijzingen naar de andere containers binnen het Docker netwerk
      - RABBITMQ_URL=amqp://admin:admin_password@rabbitmq:5672/
      - DATABASE_URL=postgresql://order_user:order_password@db:5432/order_management
    depends_on:
      - rabbitmq
      - db
    volumes:
      - ./order-management/app:/app # Hot-reloading: koppelt je lokale /app map aan de container
    restart: unless-stopped
    
Let op de paths bij build en volumes
