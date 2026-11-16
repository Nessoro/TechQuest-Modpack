# Low-overhead server tick; no block-break handlers or mining mechanics.
execute if score #enabled tqrpg_flags matches 1 run scoreboard players add #timer tqrpg_timer 1
execute if score #enabled tqrpg_flags matches 1 if score #timer tqrpg_timer matches 100.. run function techquest_rpg:step
