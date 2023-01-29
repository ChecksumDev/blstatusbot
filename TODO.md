# TODO
A list of of planned features for the bot

**If you have any ideas that would be a good fit to be here, feel free to open an issue or pull request!**

## **`/healthcheck`** *(or similar)*
This command will display multiple systems the bot tests and their current statuses. e.g. it would test replay uploading, and if the last replay it uploaded failed, it would display a warning and show that system having issues

## **API Route Testing**
Implement automatic testing for authorization, player api, leaderboard api, and replay uploading. More if needed. 

## **Dynamic Latency**
Instead of `/ping` only showing the averaged latency from the main BeatLeader server, add commands to manage hosts the bot will test latency against and their polling rate.

## **Setting multiple channels**
Currently, the `BOT_CHANNEL` is hardcoded to the `#server-status` channel in BeatLeader. This should be dynamic and or allow multiple to be set for different alerts. This would also coenside with automatic notifications of roles if enabled.

## **Statistics command**
As of now, thoughts incomplete. For now, display the amount of scores detected in the past x time frame since we are connected to the websocket.

