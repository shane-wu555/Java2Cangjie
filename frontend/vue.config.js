module.exports = {
  publicPath: '/',
  devServer: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://localhost:8080',
        changeOrigin: true
      }
    }
  },
  pages: {
    index: {
      entry: 'src/main.js',
      template: 'public/index.html',
      title: 'Java2Cangjie 转译平台'
    }
  }
}
