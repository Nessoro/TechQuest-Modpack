# Persistent flags: administrators may set #enabled/#perks/#mobs in tqrpg_flags to 0.
scoreboard objectives add tqrpg_flags dummy
scoreboard objectives add tqrpg_timer dummy
scoreboard objectives add tqrpg_days dummy
execute unless score #enabled tqrpg_flags matches 0.. run scoreboard players set #enabled tqrpg_flags 1
execute unless score #perks tqrpg_flags matches 0.. run scoreboard players set #perks tqrpg_flags 1
execute unless score #mobs tqrpg_flags matches 0.. run scoreboard players set #mobs tqrpg_flags 1
scoreboard players set #timer tqrpg_timer 0
