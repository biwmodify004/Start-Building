#property strict
#property version "1.10"
#property description "NS Capital read-only price bridge. No trading commands."

input string BridgeURL="http://127.0.0.1:8787";
input string BridgeToken="";
input double ServerUTCOffsetHours=3.0; // Set the ACTUAL current broker server UTC offset.
input int PollSeconds=2;
input bool MarketWatchOnly=true; // Add desired instruments to Market Watch first.
datetime lastCatalog=0,lastHeartbeat=0;
bool busy=false;

string J(string value){
 StringReplace(value,"\\","\\\\");StringReplace(value,"\"","\\\"");
 StringReplace(value,"\r","\\r");StringReplace(value,"\n","\\n");StringReplace(value,"\t","\\t");
 return "\""+value+"\"";
}
string N(double value,int digits=10){return DoubleToString(value,digits);}
string UTCms(datetime serverTime){return IntegerToString((long)serverTime*1000-(long)MathRound(ServerUTCOffsetHours*3600000));}
int Request(string method,string path,string body,string &answer){
 char data[],result[];string responseHeaders;
 if(StringLen(body)>0){StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);ArrayResize(data,ArraySize(data)-1);}
 string headers="Authorization: Bearer "+BridgeToken+"\r\nContent-Type: application/json\r\n";
 ResetLastError();
 int code=WebRequest(method,BridgeURL+path,headers,5000,data,result,responseHeaders);
 answer=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
 if(code<200||code>=300)Print("NS Market Bridge HTTP ",code," / MQL error ",GetLastError(),". Check bridge token, WebRequest allowed URL and gateway.");
 return code;
}
string Header(){return "\"broker\":"+J(AccountCompany())+",\"connected\":"+(IsConnected()?"true":"false")+",\"account\":{\"id\":"+J(IntegerToString(AccountNumber()))+",\"server\":"+J(AccountServer())+",\"currency\":"+J(AccountCurrency())+",\"mode\":"+J(IsDemo()?"demo":"real")+",\"balance\":"+N(AccountBalance())+",\"equity\":"+N(AccountEquity())+",\"freeMargin\":"+N(AccountFreeMargin())+"}";}
void Heartbeat(bool includeCatalog){
 string body="{"+Header();
 if(includeCatalog){
  body+=",\"symbols\":[";bool first=true;
  int total=(int)MathMin(SymbolsTotal(MarketWatchOnly),20000);
  for(int i=0;i<total;i++){
   string s=SymbolName(i,MarketWatchOnly),currency=SymbolInfoString(s,SYMBOL_CURRENCY_PROFIT);
   double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=MarketInfo(s,MODE_POINT);
   if(StringLen(currency)==0||tick<=0)continue;
   if(!first)body+=",";first=false;
   body+="{\"ticker\":"+J(s)+",\"description\":"+J(SymbolInfoString(s,SYMBOL_DESCRIPTION))+",\"path\":"+J(SymbolInfoString(s,SYMBOL_PATH))+",\"currency\":"+J(currency)+",\"tickSize\":"+N(tick,16)+",\"lotStep\":"+N(MarketInfo(s,MODE_LOTSTEP))+"}";
  }
  body+="]";
 }
 body+="}";string answer;
 if(Request("POST","/v1/mt4/publish",body,answer)==200){lastHeartbeat=TimeLocal();if(includeCatalog)lastCatalog=TimeLocal();}
}
void PublishSeries(string command){
 string parts[];ushort delimiter=StringGetCharacter("|",0);
 if(StringSplit(command,delimiter,parts)!=4)return;
 string symbol=parts[0],frame=parts[1];int limit=(int)StringToInteger(parts[2]);
 int tf=frame=="D"?PERIOD_D1:frame=="W"?PERIOD_W1:(int)StringToInteger(frame);
 if(limit<1||limit>10000||!(tf==1||tf==5||tf==15||tf==30||tf==60||tf==240||tf==1440||tf==10080))return;
 if(!SymbolSelect(symbol,true)){Print("NS: symbol is unavailable: ",symbol);return;}
 long endUTC=StringToInteger(parts[3]);int shift=0;
 if(endUTC>0){datetime endServer=(datetime)(endUTC/1000+(long)MathRound(ServerUTCOffsetHours*3600));shift=iBarShift(symbol,tf,endServer,false);if(shift<0)shift=0;}
 int count=MathMin(limit,MathMax(0,iBars(symbol,tf)-shift)),digits=(int)MarketInfo(symbol,MODE_DIGITS);
 string body="{"+Header()+",\"quotes\":[{\"symbol\":"+J(symbol)+",\"bid\":"+N(MarketInfo(symbol,MODE_BID),digits)+",\"ask\":"+N(MarketInfo(symbol,MODE_ASK),digits)+",\"time\":"+UTCms((datetime)MarketInfo(symbol,MODE_TIME))+"}],\"series\":[{\"symbol\":"+J(symbol)+",\"timeframe\":"+J(frame)+",\"bars\":[";
 bool first=true;
 for(int i=shift+count-1;i>=shift;i--){
  datetime at=iTime(symbol,tf,i);double o=iOpen(symbol,tf,i),h=iHigh(symbol,tf,i),l=iLow(symbol,tf,i),c=iClose(symbol,tf,i);
  if(at<=0||o<=0||c<=0||l<=0)continue;
  if(!first)body+=",";first=false;
  body+="{\"time\":"+UTCms(at)+",\"open\":"+N(o,digits)+",\"high\":"+N(h,digits)+",\"low\":"+N(l,digits)+",\"close\":"+N(c,digits)+",\"volume\":"+IntegerToString(iVolume(symbol,tf,i))+"}";
 }
 body+="]}]}";string answer;
 if(Request("POST","/v1/mt4/publish",body,answer)==200)lastHeartbeat=TimeLocal();
 if(count<2)Print("NS: waiting for history for ",symbol," / ",frame,". Open this chart to download history.");
}
int OnInit(){
 if(StringLen(BridgeToken)<32||ServerUTCOffsetHours< -12||ServerUTCOffsetHours>14){Print("Set BridgeToken (32+ chars) and the actual ServerUTCOffsetHours.");return INIT_PARAMETERS_INCORRECT;}
 while(StringSubstr(BridgeURL,StringLen(BridgeURL)-1)=="/") {Print("Remove trailing slash from BridgeURL.");return INIT_PARAMETERS_INCORRECT;}
 EventSetTimer(MathMax(1,PollSeconds));Print("NS read-only market bridge started. No order execution is implemented.");return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();Comment("");}
void OnTimer(){
 if(busy)return;busy=true;
 if(lastCatalog==0||TimeLocal()-lastCatalog>=60)Heartbeat(true);
 string command;int code=Request("GET","/v1/mt4/request","",command);
 if(code==200&&StringLen(command)>0)PublishSeries(command);
 else if(TimeLocal()-lastHeartbeat>=10)Heartbeat(false);
 Comment("NS Market Bridge · READ ONLY\n",IsConnected()?"Terminal connected":"Terminal offline","\nUTC offset: ",DoubleToString(ServerUTCOffsetHours,2)," h\nLast publish: ",TimeToString(lastHeartbeat,TIME_SECONDS));
 busy=false;
}
