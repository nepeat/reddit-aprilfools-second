# reddit april fools - second

my personal scripts that do things with the reddit second april fools webapp

## scripts
* read.py - reads from the websocket of the second API and publishes it to a redis pubsub channel along with saving it to a redis list.
* display.py - listens to a redis pubsub channel and posts updates to the cli
* process.py - processes all the data stored in the redis list
