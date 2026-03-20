INSERT INTO permissions (code, name)
SELECT 'notify_rooms', 'Notify Rooms'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='notify_rooms');

INSERT INTO permissions (code, name)
SELECT 'claim_notify_settings', 'Claim Notify Settings'
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='claim_notify_settings');
