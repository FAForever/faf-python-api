CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `root`@`localhost` 
    SQL SECURITY DEFINER
VIEW `clan_list` AS
    SELECT 
        `fafclans`.`clans_list`.`clan_id` AS `clan_id`,
        `fafclans`.`clans_list`.`status` AS `status`,
        `fafclans`.`clans_list`.`clan_name` AS `clan_name`,
        `fafclans`.`clans_list`.`clan_tag` AS `clan_tag`,
        `fafclans`.`clans_list`.`clan_founder_id` AS `clan_founder_id`,
        `fafclans`.`clans_list`.`clan_desc` AS `clan_desc`,
        `fafclans`.`clans_list`.`create_date` AS `create_date`,
        `faf_test`.`login`.`login` AS `founder_name`
    FROM
        (`fafclans`.`clans_list`
        LEFT JOIN `faf_test`.`login` ON ((`fafclans`.`clans_list`.`clan_founder_id` = `faf_test`.`login`.`id`)));

CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `root`@`localhost` 
    SQL SECURITY DEFINER
VIEW `clan_members` AS
    SELECT 
        `clan_members_list_view`.`clan_id` AS `clan_id`,
        `fafclans`.`clans_list`.`clan_name` AS `clan_name`,
        `fafclans`.`clans_list`.`clan_tag` AS `clan_tag`,
        `clan_members_list_view`.`player_id` AS `player_id`,
        `clan_members_list_view`.`player_name` AS `player_name`,
        `clan_members_list_view`.`join_clan_date` AS `join_clan_date`
    FROM
        (`fafclans`.`clan_members_list_view`
        LEFT JOIN `fafclans`.`clans_list` ON ((`clan_members_list_view`.`clan_id` = `fafclans`.`clans_list`.`clan_id`)));
