# ShadowChain
*本项目为杭州电子科技大学通信工程学院大学生科研创新训练计划项目课题,仅供学习交流之用*
From The Shadow  : )

## 项目初衷
此项目的本意是建立一个自动化，高度匿名的代理工具。项目特点如下：
1. 项目使用python3.4之后引入的asyncio包完成，所有io交互实现异步。所有io操作都在单一线程中完成
2. 项目引入协议栈机制，可以任意扩展第三方协议。并且通过协议栈，可以完成将单一数据包裹复数协议的方式传送。达到链式代理的目的。
3. 入上所言，项目可以任意扩展协议的数量，通过后续开发，可以支持复数协议。


## 协议开发
协议可以抽象的分成两种，server协议和client协议。程序运行时会使用一种server协议来监听某端口。作为代理数据的输入。client协议端支持复数的协议栈，通过回调函数的方式层级传播数据。

由于是瞎写着玩，开发接口耦合严重。撸协议自己阅读`protocol.BaseServer`源码。此类继承自[asyncio.Protocol](https://docs.python.org/3/library/asyncio-protocol.html#protocols)。所以支持protocol中所有回调。

> BaseServer.loop

创建类的时候传入的event_loop实例，异步调用会使用此loop

> BaseServer.transport

connection_made时传入的和此protocol对应的transport方法。请及时保存。

> BaseServer.peer_transport

这个东西是对端，也就是client端的transport实例，不过不推荐直接读写，所有数据因通过协议栈打包发送

> BaseServer.peer_proto

client端协议的实例，为`BaseClientTop`类。协议栈入口。

> BaseServer.write(self, data)

当client端有数据到来的时候会调用此方法。

> BaseServer.connection_lost(self, exc)

类中有一些默认操作，重载时请保留

> BaseServer.handle_peer_close

当对端关闭的时候会调用此方法，表示如何处理此问题。默认方法是调用raw_close()

> BaseServer.notify_ignore

设置为True，则`handle_peer_close`不会被调用。

