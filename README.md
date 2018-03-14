[![PyPI version](https://img.shields.io/pypi/v/shadowChain.svg)](https://pypi.python.org/pypi/shadowChain/0.0.1)
[![License](https://img.shields.io/pypi/l/shadowChain.svg)](https://pypi.python.org/pypi/shadowChain/0.0.1)
# ShadowChain
*本项目为杭州电子科技大学通信工程学院大学生科研创新训练计划项目课题,仅供学习交流之用*
From The Shadow  : )

## 项目初衷
此项目的本意是建立一个自动化，高度匿名的代理工具。项目特点如下：
1. 项目使用python3.4之后引入的asyncio包完成，所有io交互实现异步。所有io操作都在单一线程中完成
2. 项目引入协议栈机制，可以任意扩展第三方协议。并且通过协议栈，可以完成将单一数据包裹复数协议的方式传送。达到链式代理的目的。
3. 如上所言，项目可以任意扩展协议的数量，通过后续开发，可以支持复数协议。


## 安装
此项目需要python3.5版本以上

> pip3 install shadowChain

## 使用
使用
> SCStart confg.json

启动进程

该项目使用json作为配置文件格式。配置如下
```json
{
  "in_protocol": [
    "Socks5"
  ],
  "server_host": "0.0.0.0",
  "server_port": 3333,
  "out_protocol": [
    {
      "name": "SCSProxy",
      "host": "108.61.171.167",
      "port": 443
    },
    {
      "name": "SC"
    }
  ],
  "password": "you_password",
  "is_reverse_server": false,
  "is_reverse_client": false
}
```

其中`in_protocol`为输入协议，可以选择socks5或者SC协议作为server协议，同时需要指定`server_host`，`server_port`作为服务监听的端口以启动服务。

`out_protocol`为输出协议,协议栈中的每个协议默认必须具有`name`属性，若协议为代理协议，则通常具有`host`与`port`属性。

`password`为用户密码。`is_reverse_server`和`is_reverse_client`为非必要属性。开启`is_reverse_server`表示本服务器为NAT穿透时处在内网中的server端。此时指定`server_host`，`server_port`作为公网的转发服务器地址。而开启`is_reverse_client`表示本服务器在作为公网转发服务器,接受来自内网的连接，此时`out_protocol`中最后一个被指定的地址作为服务器的监听地址。

### 协议栈
这里我将协议分为三种类型， base类型，client类型，server类型。

base类型不具有代理转发的功能。只对数据进行一定的变换，通常为全局的加密协议。

client类型作为代理协议的客户端部分，有两个额外的参数`host`与`port`来表明该客户端所对应的服务端地址。

server类型作为协议的服务端部分，通常会解析出连接需要转发到的实际地址。

在配置文件中，`in_protocol`和`out_protocol`皆为数组，接受object（有额外参数）或者纯字符串（无额外参数）类型。

其中`in_protocol`接受一个server类型协议，且必须为第一个，和多个base类型协议。如此，端口接受到的网络数据将按照从后往前的顺序经过各个协议解码，最后解析出发送的源数据与需要到达的目标。

而`in_protocol`任意数量的client协议与base协议。若为client协议，则需要使用object来一并传入服务端地址`host`和`port`。此地址会作为要转发的目标地址传递给下一个client协议，如此完成出口代理栈。通过多成包装，可以让数据经过多台不同协议网络节点的转发最终达到目标地址。注意，协议栈中的最后一个client协议的目的地址即为该服务器的时间连接地址。若协议栈中无client协议，则默认以server端解析出目标地址作为连接地址，实现代理链的最终出口访问。虽然此时可以添加base协议以编码输出，但通常会产生错误。

## 协议

### socks5协议
代理实现了基础的socks5协议，可以实现socks5转发。类型为server或者client，根据协议出现位置决定。

PS：不建议使用socks5作为向公网转发的协议，因为socks5为明文协议且特征明显。只推荐作为高性能的本机转发协议。

### SC协议
类型为base协议，为此项目特有协议。主要作用是加密流量，隐藏流量特征。SC协议配置中可以传入额外的参数timeout用以控制包超时时间。由于防重放算法的原因，若包的发送时间与服务器接受到此包的时间超过timeout设定的误差，则直接断开连接。请保证timeout时间在本机与代理服务器延迟之上。默认值为300s，若设为0。则关闭防重放检测。

PS：强烈推荐将SC协议作为协议栈的最终协议，进行全局的数据加密，以保障安全。

具体请查阅SC协议文档.pdf

### SCProxy协议
与socks5类似的简化代理协议，删除了socks5中不必要的内容。类型为server或者client，根据协议出现位置决定。

推荐将其与SC协议配套使用，最为代理转发协议

### PF协议
端口转发协议，类型为server，且具有额外的`host`和`port`参数。所有发送到此协议的数据其目标地址均为`host`和`port`指定地址。可以保证数据最终发往此地址，作为端口转发协议使用。