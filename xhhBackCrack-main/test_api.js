#!/usr/bin/env node

const https = require('https');
const { generateRequestUrl, ROUTES } = require('./Hkey.js');
const localAuth = require('./local_auth.js');

function showUsage() {
    console.log('\n使用方法:');
    console.log('  node test_api.js [路由名称] [key=value 参数]');
    console.log('\n示例:');
    console.log('  node test_api.js');
    console.log('  node test_api.js emojis_list');
    console.log('  node test_api.js general_search_v1 q=模拟');
    console.log('  node test_api.js feeds offset=0 dw=1920');
    console.log('  node test_api.js user_profile userid=12345678');
    console.log('  node test_api.js related_recommend_web link_id=175495445 h_src=FxDNnklDNXqYrPXG7');
    console.log('\n说明:');
    console.log('  默认路由是 emojis_list');
    console.log('  该脚本会先生成签名 URL，再实际发起 GET 请求');
    console.log('  默认读取当前目录下的 local_auth.js');
    console.log('');
}

function parseArgs(argv) {
    const args = argv.slice(2);
    if (args.includes('--help') || args.includes('-h')) {
        return { help: true };
    }

    let routeName = 'emojis_list';
    let startIndex = 0;

    if (args[0] && !args[0].includes('=')) {
        routeName = args[0];
        startIndex = 1;
    }

    const customParams = {};
    const runtimeOptions = {};
    for (let i = startIndex; i < args.length; i++) {
        const arg = args[i];
        if (!arg.includes('=')) {
            continue;
        }
        const [key, ...rest] = arg.split('=');
        const value = rest.join('=');

        if (key === '__cookie') {
            runtimeOptions.cookie = value;
            continue;
        }
        if (key === '__ua') {
            runtimeOptions.userAgent = value;
            continue;
        }
        if (key === '__referer') {
            runtimeOptions.referer = value;
            continue;
        }
        if (key === '__origin') {
            runtimeOptions.origin = value;
            continue;
        }

        customParams[key] = value;
    }

    return { help: false, routeName, customParams, runtimeOptions };
}

function getRuntimeConfig(runtimeOptions = {}) {
    const referer = runtimeOptions.referer || localAuth.referer || process.env.XHH_REFERER || 'https://www.xiaoheihe.cn/';
    const origin = runtimeOptions.origin || localAuth.origin || process.env.XHH_ORIGIN || 'https://www.xiaoheihe.cn';
    const userAgent = runtimeOptions.userAgent || localAuth.userAgent || process.env.XHH_USER_AGENT || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36';
    const cookie = runtimeOptions.cookie || localAuth.cookie || process.env.XHH_COOKIE || '';

    const baseOverrides = {
        heybox_id: localAuth.heyboxId || process.env.XHH_HEYBOX_ID || '',
        x_os_type: localAuth.xOsType || process.env.XHH_X_OS_TYPE || 'Windows',
        device_info: localAuth.deviceInfo || process.env.XHH_DEVICE_INFO || 'Chrome',
        device_id: localAuth.deviceId || process.env.XHH_DEVICE_ID || '2c2fef8385ccef915e3b3caf94e3aa06'
    };

    return {
        cookie,
        headers: {
            'accept': 'application/json, text/plain, */*',
            'origin': origin,
            'referer': referer,
            'user-agent': userAgent
        },
        baseOverrides
    };
}

function doGet(url, headers) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, {
            headers
        }, (res) => {
            let body = '';
            res.setEncoding('utf8');

            res.on('data', (chunk) => {
                body += chunk;
            });

            res.on('end', () => {
                resolve({
                    statusCode: res.statusCode,
                    statusMessage: res.statusMessage,
                    headers: res.headers,
                    body
                });
            });
        });

        req.on('error', reject);
        req.end();
    });
}

function printJsonSummary(json) {
    if (typeof json !== 'object' || json === null) {
        return;
    }

    if ('result' in json) {
        if (Array.isArray(json.result)) {
            console.log(`result: array(${json.result.length})`);
        } else if (json.result && typeof json.result === 'object') {
            console.log(`result keys: ${Object.keys(json.result).slice(0, 12).join(', ') || '(empty object)'}`);
        } else {
            console.log(`result: ${json.result}`);
        }
    }
    if ('code' in json) {
        console.log(`code: ${json.code}`);
    }
    if ('msg' in json) {
        console.log(`msg: ${json.msg}`);
    }
    if ('message' in json) {
        console.log(`message: ${json.message}`);
    }
    if ('data' in json) {
        if (Array.isArray(json.data)) {
            console.log(`data: array(${json.data.length})`);
        } else if (json.data && typeof json.data === 'object') {
            console.log(`data keys: ${Object.keys(json.data).slice(0, 12).join(', ') || '(empty object)'}`);
        } else {
            console.log(`data: ${json.data}`);
        }
    }
}

async function main() {
    const { help, routeName, customParams, runtimeOptions } = parseArgs(process.argv);
    if (help) {
        showUsage();
        return;
    }

    if (!ROUTES[routeName]) {
        console.error(`未知路由: ${routeName}`);
        console.error(`可用路由: ${Object.keys(ROUTES).join(', ')}`);
        process.exitCode = 1;
        return;
    }

    const runtimeConfig = getRuntimeConfig(runtimeOptions);
    const headers = { ...runtimeConfig.headers };
    if (runtimeConfig.cookie) {
        headers.cookie = runtimeConfig.cookie;
    }

    const requestInfo = generateRequestUrl(routeName, customParams, runtimeConfig.baseOverrides);

    console.log('='.repeat(60));
    console.log('小黑盒 API 测试');
    console.log('='.repeat(60));
    console.log(`route: ${routeName}`);
    console.log(`path: ${requestInfo.path}`);
    console.log(`hkey: ${requestInfo.hkey}`);
    console.log(`timestamp: ${requestInfo.timestamp}`);
    console.log(`nonce: ${requestInfo.nonce}`);
    console.log(`url: ${requestInfo.url}`);
    console.log(`cookie: ${runtimeConfig.cookie ? 'provided' : 'not provided'}`);
    console.log('');

    try {
        const response = await doGet(requestInfo.url, headers);
        console.log(`HTTP: ${response.statusCode} ${response.statusMessage}`);
        console.log(`content-type: ${response.headers['content-type'] || ''}`);
        console.log('');

        try {
            const json = JSON.parse(response.body);
            printJsonSummary(json);
            console.log('\nresponse json:');
            console.log(JSON.stringify(json, null, 2));
        } catch {
            console.log('response text:');
            console.log(response.body.slice(0, 4000));
        }
    } catch (error) {
        console.error(`请求失败: ${error.message}`);
        process.exitCode = 1;
    }
}

main();
