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
        `founder`.`login` AS `founder_name`,
        `fafclans`.`clan_leader`.`player_id` AS `leader_id`,
        `leader`.`login` AS `leader_name`,
        (SELECT 
                COUNT(0)
            FROM
                `faf_test`.`clan_members`
            WHERE
                (`clan_members`.`clan_id` = `fafclans`.`clans_list`.`clan_id`)) AS `member_count`
    FROM
        (((`fafclans`.`clans_list`
        LEFT JOIN `faf_test`.`login` `founder` ON ((`fafclans`.`clans_list`.`clan_founder_id` = `founder`.`id`)))
        LEFT JOIN `fafclans`.`clan_leader` ON ((`fafclans`.`clans_list`.`clan_id` = `fafclans`.`clan_leader`.`clan_id`)))
        LEFT JOIN `faf_test`.`login` `leader` ON ((`fafclans`.`clan_leader`.`player_id` = `leader`.`id`)));

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
