
// craco.config.js

module.exports = {
  devServer: (devServerConfig) => {
    // Force webpack-dev-server to accept rezify.local
    devServerConfig.allowedHosts = ['rezify.local', 'localhost'];

    return devServerConfig;
  },
};