CREATE TABLE IF NOT EXISTS topics
(
    id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    priority_level INT NOT NULL,
    users_in_favor BIGINT[],
    message_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    thread_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings
(
    guild_id BIGINT PRIMARY KEY,
    output_channel_id BIGINT,
    allowed_role_ids BIGINT[],
    priority_counting_thread BIGINT,
    status_thread_id BIGINT
);
