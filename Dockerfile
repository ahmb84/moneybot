FROM        python:3.6-alpine

# Create a user to run the application
RUN         adduser -D burry
WORKDIR     /home/burry

# Add application files
COPY        examples ./examples
COPY        moneybot ./moneybot
COPY        config.yml requirements.txt setup.py ./

# Install dependencies
RUN         pip install -U pip && pip install -r ./requirements.txt

USER        burry
ENTRYPOINT  ["python3", "examples/live_trading.py", "-c", "config.yml"]
