# World age is a proxy for progression; avoids player levels and PMMO XP completely.
execute store result score #day tqrpg_days run time query day
execute if score #day tqrpg_days matches 7..20 run function techquest_rpg:mob_tier1
execute if score #day tqrpg_days matches 21..41 run function techquest_rpg:mob_tier2
execute if score #day tqrpg_days matches 42.. run function techquest_rpg:mob_tier3
