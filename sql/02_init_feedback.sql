-- 用户反馈表初始化脚本
-- 用于收集用户对 Agent 回复的反馈（👍/👎）

-- 创建反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down')),
    user_comment TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(session_id, message_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_intent ON user_feedback((metadata->>'intent'));
CREATE INDEX IF NOT EXISTS idx_feedback_skill ON user_feedback((metadata->>'skill_name'));
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);

-- 添加注释
COMMENT ON TABLE user_feedback IS '用户反馈表，记录用户对 Agent 回复的评价';
COMMENT ON COLUMN user_feedback.session_id IS '会话 ID';
COMMENT ON COLUMN user_feedback.message_id IS '消息 ID（Agent 回复的唯一标识）';
COMMENT ON COLUMN user_feedback.feedback_type IS '反馈类型：thumbs_up（👍）或 thumbs_down（👎）';
COMMENT ON COLUMN user_feedback.user_comment IS '用户可选的评论说明';
COMMENT ON COLUMN user_feedback.metadata IS '元数据（JSON 格式），包含意图、Skill、参数等';
COMMENT ON COLUMN user_feedback.created_at IS '创建时间';
COMMENT ON COLUMN user_feedback.updated_at IS '更新时间';
