SELECT
    STATE AS state_name,
    EVENT_TYPE AS event_type,
    COALESCE(DAMAGE_PROPERTY, 0) AS property_damage,
    COALESCE(DAMAGE_CROPS, 0) AS crop_damage
FROM StormEvents
WHERE EVENT_TYPE IS NOT NULL;
