#!/usr/bin/env node

const { generateRequestUrl, listRoutes, ROUTES } = require('./Hkey.js');

// 获取命令行参数
const args = process.argv.slice(2);

// 显示使用说明
function showUsage() {
    console.log('\n使用方法:');
    console.log('  node generate.js <路由名称> [自定义参数]');
    console.log('\n示例:');
    console.log('  node generate.js emojis_list');
    console.log('  node generate.js feeds offset=20 dw=1920');
    console.log('\n查看所有可用路由:');
    console.log('  node generate.js --list');
    console.log('');
}

// 解析自定义参数
function parseCustomParams(args) {
    const params = {};
    for (let i = 1; i < args.length; i++) {
        const arg = args[i];
        if (arg.includes('=')) {
            const [key, value] = arg.split('=');
            params[key] = value;
        }
    }
    return params;
}

// 主函数
function main() {
    // 没有参数或帮助命令
    if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
        showUsage();
        listRoutes();
        return;
    }

    // 列出所有路由
    if (args[0] === '--list' || args[0] === '-l') {
        listRoutes();
        return;
    }

    // 生成请求链接
    const routeName = args[0];
    const customParams = parseCustomParams(args);

    try {
        const result = generateRequestUrl(routeName, customParams);

        console.log('\n' + '='.repeat(60));
        console.log('请求链接生成成功!');
        console.log('='.repeat(60));
        console.log(`\n路由名称: ${routeName}`);
        console.log(`路径: ${result.path}`);
        console.log(`hkey: ${result.hkey}`);
        console.log(`时间戳: ${result.timestamp}`);
        console.log(`nonce: ${result.nonce}`);
        console.log(`\n完整URL:\n${result.url}`);
        console.log('\n' + '='.repeat(60) + '\n');
    } catch (error) {
        console.error(`\n错误: ${error.message}\n`);
        showUsage();
        listRoutes();
    }
}

// 运行主函数
main();
