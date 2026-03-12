const nextConfig = {
    output: 'export',
    images: {
        unoptimized: true,
    },
    trailingSlash: true,
    env: {
        NEXT_PUBLIC_MY_AWESOME_AGENT_URL: 'wss://voice-agent-backend-o4dv7heaia-uc.a.run.app/ws',
    },
};

module.exports = nextConfig;
