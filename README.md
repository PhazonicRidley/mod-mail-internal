# mod-mail-internal

This bot is to anonymously bring up and keep track of discussion topics for teams. 
It can be hard to discuss things out in the open, so the idea with this is to allow for an "open field free(er) of bias" to discuss potentially hard subjects.

# Self Hosting
Self hosting is made simple by using docker however this bot can be ran without docker however this is not recommended.

### Instructions for docker
1) Clone this repo to the machine you want to run it on
3) Make sure docker and compose are installed to that machine
5) Go into the directory with the repo
6) Edit the `config.yml.example` file to be a `config.yml` and add your token. Be sure to uncomment the docker version of the database credentials.
7) If you wish to change your database's username or password, you can do so in the `docker-compose.yml` file under the `POSTGRES_USER` and `POSTGRES_PASSWORD` labels
8) Start the bot for the first time with `docker-compose up -d`
9) Add your bot to a server.
10) Finally run `)sync` in your server so discord is updated with the bot's commands!

To stop the bot use `docker-compose stop` and to restart it use `docker-compose start`
Please note: if you ever use `docker-compose down` to delete this compose system, the database will be removed so be sure to back it up!

# Usage

Please note that this bot is in beta and needs more rigorous testing, as well as missing a couple of minor features.

This bot exclusively uses slash (app) commands. Configuration is done on a server by server basis by those with the `administrator` permissions.

Create a forum channel and use `/channel set` to set that channel.
Then add the roles you wish to be able to create discussion topics with `/role set`.
Users with allowed roles will be able to make topics by using `/topic create`
People in the channel will then be able to add priority to a topic by using the buttons on the first message in the newly created topic thread.
Once a discussion has reached its conclusion, an admin can close the topic with `/topic close`. 
People can edit (with `/topic edit`) and close their own threads as well.

# Planned features
- Ordering of the threads in the channel by priority
- Adding tags for topics
- Reopening old threads
- Cleaning up the way data is stored in the database
- CI/CD
