# Tipos de eventos que auth publica. La idea original era que estuviera en su propio fichero events.py
# pero me he puesto quisquilloso para intentar que encajara en una capa de nuestros dominios.
# Recuerdo que un esquema es el contrato que define la interacción del dominio con el exterior de la API.
# En este caso lo exterior de la API es la publicación en Kafka del evento.

USER_REGISTERED = "user.registered"
