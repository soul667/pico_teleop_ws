declare module 'roslib' {
  export class Ros {
    constructor(options: { url: string });
    on(event: string, callback: (...args: any[]) => void): void;
    close(): void;
  }
  export class Topic {
    constructor(options: { ros: Ros; name: string; messageType: string });
    publish(msg: Message): void;
    subscribe(callback: (msg: any) => void): void;
    unsubscribe(): void;
  }
  export class Service {
    constructor(options: { ros: Ros; name: string; serviceType: string });
    callService(request: ServiceRequest, callback: (res: any) => void, errorCallback?: (err: any) => void): void;
  }
  export class Message {
    constructor(values: Record<string, any>);
  }
  export class ServiceRequest {
    constructor(values: Record<string, any>);
  }
}
