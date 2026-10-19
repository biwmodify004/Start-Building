#property strict
#property version "1.80"
#property description "NS Capital gateway. Manual orders require EnableTrading and a separate TradeToken."

input string BridgeURL="http://127.0.0.1:8787";
input string BridgeToken="";
input string PublishToken=""; // EA-only publisher token; never enter it in the website.
input bool HistoryReady=false; // First select Account History > All History.
input int HistoryDays=90;
input bool EnableTrading=false;
input string TradeToken="";
input double ServerUTCOffsetHours=3.0; // Set the ACTUAL current broker server UTC offset.
input int PollSeconds=2;
input bool MarketWatchOnly=true; // Add desired instruments to Market Watch first.
datetime lastCatalog=0,lastHeartbeat=0;
bool busy=false;
string pendingReceipt="";
datetime lastHistory=0,historyThrough=0,historyFrom=0;
int historyCursor=0,historyCount=0,historyBatch=0,historyLogin=0;
string historyRun="",historyServer="";
double historyBalance=0,historyCredit=0;

string J(string value){
 StringReplace(value,"\\","\\\\");StringReplace(value,"\"","\\\"");
 StringReplace(value,"\r","\\r");StringReplace(value,"\n","\\n");StringReplace(value,"\t","\\t");
 return "\""+value+"\"";
}
string N(double value,int digits=10){return DoubleToString(value,digits);}
string UTCms(datetime serverTime){return IntegerToString((long)serverTime*1000-(long)MathRound(ServerUTCOffsetHours*3600000));}
int Request(string method,string path,string body,string &answer,bool trade=false){
 char data[],result[];string responseHeaders;
 if(StringLen(body)>0){StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);ArrayResize(data,ArraySize(data)-1);}
 string headers="Authorization: Bearer "+BridgeToken+"\r\nContent-Type: application/json\r\n";
 headers+="X-Publish-Token: "+PublishToken+"\r\n";
 if(trade)headers+="X-Trade-Token: "+TradeToken+"\r\n";
 ResetLastError();
 int code=WebRequest(method,BridgeURL+path,headers,5000,data,result,responseHeaders);
 answer=CharArrayToString(result,0,WHOLE_ARRAY,CP_UTF8);
 if(code<200||code>=300)Print("NS Market Bridge HTTP ",code," / MQL error ",GetLastError(),". Check bridge token, WebRequest allowed URL and gateway.");
 return code;
}
string PositionsJSON(){
 string value="[";bool first=true;
 for(int i=0;i<OrdersTotal();i++)if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES)&&OrderType()<=OP_SELL){
  string symbol=OrderSymbol();int digits=(int)MarketInfo(symbol,MODE_DIGITS);
  if(!first)value+=",";first=false;
  value+="{\"ticket\":"+J(IntegerToString(OrderTicket()))+",\"symbol\":"+J(symbol)+",\"side\":"+J(OrderType()==OP_BUY?"buy":"sell")+",\"volume\":"+N(OrderLots())+",\"entry\":"+N(OrderOpenPrice(),digits)+",\"price\":"+N(MarketInfo(symbol,OrderType()==OP_BUY?MODE_BID:MODE_ASK),digits)+",\"sl\":"+N(OrderStopLoss(),digits)+",\"tp\":"+N(OrderTakeProfit(),digits)+",\"profit\":"+N(OrderProfit())+",\"swap\":"+N(OrderSwap())+",\"commission\":"+N(OrderCommission())+",\"time\":"+UTCms(OrderOpenTime())+"}";
 }
 return value+"]";
}
string PositionQuotesJSON(){
 string value="[";bool first=true;
 for(int i=0;i<OrdersTotal();i++)if(OrderSelect(i,SELECT_BY_POS,MODE_TRADES)&&OrderType()<=OP_SELL){
  string s=OrderSymbol();int digits=(int)MarketInfo(s,MODE_DIGITS);datetime at=(datetime)MarketInfo(s,MODE_TIME);
  if(at<=0||MarketInfo(s,MODE_BID)<=0||MarketInfo(s,MODE_ASK)<=0)continue;
  if(!first)value+=",";first=false;
  value+="{\"symbol\":"+J(s)+",\"bid\":"+N(MarketInfo(s,MODE_BID),digits)+",\"ask\":"+N(MarketInfo(s,MODE_ASK),digits)+",\"time\":"+UTCms(at)+"}";
 }
 return value+"]";
}
string Header(){return "\"broker\":"+J(AccountCompany())+",\"connected\":"+(IsConnected()?"true":"false")+",\"account\":{\"id\":"+J(IntegerToString(AccountNumber()))+",\"server\":"+J(AccountServer())+",\"currency\":"+J(AccountCurrency())+",\"mode\":"+J(IsDemo()?"demo":"real")+",\"balance\":"+N(AccountBalance())+",\"equity\":"+N(AccountEquity())+",\"freeMargin\":"+N(AccountFreeMargin())+",\"credit\":"+N(AccountCredit())+"},\"tradeAllowed\":"+((EnableTrading&&StringLen(TradeToken)>=32&&IsTradeAllowed()&&IsConnected())?"true":"false")+",\"positions\":"+PositionsJSON();}
void Heartbeat(bool includeCatalog){
 string body="{"+Header()+",\"quotes\":"+PositionQuotesJSON();
 if(includeCatalog){
  body+=",\"symbols\":[";bool first=true;
  int total=(int)MathMin(SymbolsTotal(MarketWatchOnly),20000);
  for(int i=0;i<total;i++){
   string s=SymbolName(i,MarketWatchOnly),currency=SymbolInfoString(s,SYMBOL_CURRENCY_PROFIT);
   double tick=SymbolInfoDouble(s,SYMBOL_TRADE_TICK_SIZE);if(tick<=0)tick=MarketInfo(s,MODE_POINT);
   if(StringLen(currency)==0||tick<=0)continue;
   if(!first)body+=",";first=false;
   body+="{\"ticker\":"+J(s)+",\"description\":"+J(SymbolInfoString(s,SYMBOL_DESCRIPTION))+",\"path\":"+J(SymbolInfoString(s,SYMBOL_PATH))+",\"currency\":"+J(currency)+",\"tickSize\":"+N(tick,16)+",\"tickValue\":"+N(MarketInfo(s,MODE_TICKVALUE))+",\"lotStep\":"+N(MarketInfo(s,MODE_LOTSTEP))+",\"volumeMin\":"+N(MarketInfo(s,MODE_MINLOT))+",\"volumeMax\":"+N(MarketInfo(s,MODE_MAXLOT))+",\"point\":"+N(MarketInfo(s,MODE_POINT),16)+",\"stopsLevel\":"+N(MarketInfo(s,MODE_STOPLEVEL))+"}";
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
void PublishHistory(){
 if(!HistoryReady)return;
 if(StringLen(historyRun)==0){
  if(lastHistory>0&&TimeLocal()-lastHistory<30)return;
  historyThrough=TimeGMT();historyFrom=historyThrough-(datetime)(MathMax(2,MathMin(3650,HistoryDays))*86400);
  historyCount=OrdersHistoryTotal();historyCursor=0;historyBatch=0;historyLogin=AccountNumber();historyServer=AccountServer();
  historyBalance=AccountBalance();historyCredit=AccountCredit();
  historyRun=IntegerToString((long)TimeLocal())+"_"+IntegerToString((long)GetTickCount());
 }
 if(historyLogin!=AccountNumber()||historyServer!=AccountServer()||OrdersHistoryTotal()!=historyCount){historyRun="";return;}
 int nextCursor=historyCursor,added=0,scanned=0;string rows="";
 while(nextCursor<historyCount&&added<200&&scanned<10000){
  int atIndex=nextCursor;nextCursor++;scanned++;
  if(!OrderSelect(atIndex,SELECT_BY_POS,MODE_HISTORY))continue;
  int type=OrderType();if(type>=2&&type<=5&&OrderProfit()==0&&OrderCommission()==0&&OrderSwap()==0)continue;
  datetime at=OrderCloseTime();if(at<=0)at=OrderOpenTime();
  long utc=StringToInteger(UTCms(at));if(utc<(long)historyFrom*1000||utc>(long)historyThrough*1000)continue;
  if(added>0)rows+=",";added++;
  rows+="{\"ticket\":"+J(IntegerToString(OrderTicket()))+",\"position_id\":"+J(IntegerToString(OrderTicket()))+",\"order\":"+J(IntegerToString(OrderTicket()))+",\"time_msc\":"+IntegerToString(utc)+",\"opened_at\":"+UTCms(OrderOpenTime())+",\"entry_price\":"+N(OrderOpenPrice())+",\"type\":"+IntegerToString(type)+",\"entry\":1,\"symbol\":"+J(OrderSymbol())+",\"volume\":"+N(OrderLots())+",\"price\":"+N(OrderClosePrice())+",\"profit\":"+N(OrderProfit())+",\"commission\":"+N(OrderCommission())+",\"swap\":"+N(OrderSwap())+",\"fee\":0,\"comment\":"+J(OrderComment())+"}";
 }
 bool complete=nextCursor>=historyCount;
 string body="{\"accountKey\":"+J(historyServer+"|"+IntegerToString(historyLogin))+",\"runId\":"+J(historyRun)+",\"batch\":"+IntegerToString(historyBatch)+",\"from\":"+IntegerToString((long)historyFrom*1000)+",\"through\":"+IntegerToString((long)historyThrough*1000)+",\"snapshotBalance\":"+N(historyBalance)+",\"snapshotCredit\":"+N(historyCredit)+",\"complete\":"+(complete?"true":"false")+",\"deals\":["+rows+"]}";
 string answer;int code=Request("POST","/v1/mt4/history",body,answer);
 if(code==200){historyCursor=nextCursor;historyBatch++;if(complete){historyRun="";lastHistory=TimeLocal();}}
 else if(code==400){historyRun="";}
}
bool GridAligned(double value,double step){return step>0&&MathAbs(value/step-MathRound(value/step))<0.000001;}
void TradePoll(){
 if(!EnableTrading||StringLen(TradeToken)<32)return;
 string answer;
 if(StringLen(pendingReceipt)>0){if(Request("POST","/v1/mt4/trade-result",pendingReceipt,answer,true)==200)pendingReceipt="";return;}
 string command;if(Request("GET","/v1/mt4/trade-request","",command,true)!=200||StringLen(command)==0)return;
 string fields[];if(StringSplit(command,StringGetCharacter("|",0),fields)!=13){Print("Invalid NS trade command");return;}
 string id=fields[0],action=fields[1],symbol=fields[2],side=fields[3],server=fields[10];
 double volume=StringToDouble(fields[4]),sl=StringToDouble(fields[5]),tp=StringToDouble(fields[6]),reference=StringToDouble(fields[12]);
 int deviation=(int)StringToInteger(fields[7]),ticket=(int)StringToInteger(fields[8]);
 long login=StringToInteger(fields[9]),expires=StringToInteger(fields[11]);
 int error=0;string message="",status="rejected";
 if(login!=AccountNumber()||server!=AccountServer())message="Account changed before execution";
 else if((long)TimeGMT()*1000>expires)message="Trade command expired";
 else if(!IsConnected()||!IsTradeAllowed())message="MT4 trading permission unavailable";
 else if(action!="open"&&action!="close"&&action!="modify")message="Unsupported action";
 else if(side!="buy"&&side!="sell")message="Invalid side";
 else if(!SymbolSelect(symbol,true))message="Symbol unavailable";
 else {
  RefreshRates();int digits=(int)MarketInfo(symbol,MODE_DIGITS);double point=MarketInfo(symbol,MODE_POINT),tick=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE),bid=MarketInfo(symbol,MODE_BID),ask=MarketInfo(symbol,MODE_ASK),price=side=="buy"?ask:bid;
  datetime tickAt=(datetime)MarketInfo(symbol,MODE_TIME);long tickAge=(long)TimeGMT()*1000-StringToInteger(UTCms(tickAt));
  if(tick<=0)tick=point;
  if(tickAge>10000||tickAge< -5000||bid<=0||ask<bid)message="No fresh MT4 quote";
  else if(deviation<0||deviation>100||action!="modify"&&MathAbs(price-reference)>deviation*point+point*0.000001)message="Price moved beyond reviewed deviation";
  else if(action!="open"&&(!OrderSelect(ticket,SELECT_BY_TICKET)||OrderCloseTime()!=0||OrderSymbol()!=symbol||OrderType()>OP_SELL))message="Position changed or closed";
  else if(action!="modify"&&(volume<MarketInfo(symbol,MODE_MINLOT)||volume>MarketInfo(symbol,MODE_MAXLOT)||!GridAligned(volume,MarketInfo(symbol,MODE_LOTSTEP))))message="Invalid broker volume";
  else if(action!="open"&&MathAbs(OrderLots()-volume)>0.00000001)message="Position volume changed";
  else if(action=="modify"&&(OrderType()==OP_BUY?"buy":"sell")!=side)message="Position side changed";
  else if(action=="close"&&(OrderType()==OP_BUY?"sell":"buy")!=side)message="Position changed before close";
  else if((sl>0&&!GridAligned(sl,tick))||(tp>0&&!GridAligned(tp,tick)))message="SL/TP off tick grid";
  else {
   double base=side=="buy"?bid:ask,distance=MarketInfo(symbol,MODE_STOPLEVEL)*point;
   bool stopsOK=action=="close"||((sl==0||(side=="buy"?base-sl:sl-base)>=distance&&(side=="buy"?base-sl:sl-base)>0)&&(tp==0||(side=="buy"?tp-base:base-tp)>=distance&&(side=="buy"?tp-base:base-tp)>0));
   if(!stopsOK)message="SL/TP invalid at execution price";
   else {
    ResetLastError();bool ok=false;
    if(action=="open"){ticket=OrderSend(symbol,side=="buy"?OP_BUY:OP_SELL,volume,NormalizeDouble(price,digits),deviation,NormalizeDouble(sl,digits),NormalizeDouble(tp,digits),"NS Capital manual",260019,0,clrNONE);ok=ticket>0;}
    else if(action=="close")ok=OrderClose(ticket,volume,NormalizeDouble(price,digits),deviation,clrNONE);
    else ok=OrderModify(ticket,OrderOpenPrice(),NormalizeDouble(sl,digits),NormalizeDouble(tp,digits),0,clrNONE);
    error=GetLastError();status=ok?"filled":error==128?"unknown":"rejected";message=ok?"MT4 execution confirmed":"MT4 returned error "+IntegerToString(error)+". Check terminal before another action";
   }
  }
 }
 pendingReceipt="{\"requestId\":"+J(id)+",\"status\":"+J(status)+",\"message\":"+J(message)+",\"order\":"+J(IntegerToString(ticket))+",\"retcode\":"+IntegerToString(error)+"}";
 if(Request("POST","/v1/mt4/trade-result",pendingReceipt,answer,true)==200)pendingReceipt="";
 Heartbeat(false);
}
int OnInit(){
 if(StringLen(PublishToken)<32||PublishToken==BridgeToken||PublishToken==TradeToken){Print("Set the separate EA-only PublishToken from Bridge.");return INIT_PARAMETERS_INCORRECT;}
 if(StringLen(BridgeToken)<32||ServerUTCOffsetHours< -12||ServerUTCOffsetHours>14){Print("Set BridgeToken (32+ chars) and the actual ServerUTCOffsetHours.");return INIT_PARAMETERS_INCORRECT;}
 while(StringSubstr(BridgeURL,StringLen(BridgeURL)-1)=="/") {Print("Remove trailing slash from BridgeURL.");return INIT_PARAMETERS_INCORRECT;}
 if(EnableTrading&&StringLen(TradeToken)<32){Print("Trading requires the separate TradeToken.");return INIT_PARAMETERS_INCORRECT;}
 EventSetTimer(MathMax(1,PollSeconds));Print(EnableTrading?"NS manual trading bridge enabled":"NS market data bridge enabled");return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();Comment("");}
void OnTimer(){
 if(busy)return;busy=true;
 if(lastCatalog==0||TimeLocal()-lastCatalog>=60)Heartbeat(true);else if(EnableTrading)Heartbeat(false);
 TradePoll();
 PublishHistory();
 string command;int code=Request("GET","/v1/mt4/request","",command);
 if(code==200&&StringLen(command)>0)PublishSeries(command);
 else if(TimeLocal()-lastHeartbeat>=10)Heartbeat(false);
 Comment(EnableTrading?"NS Bridge · MANUAL TRADING\n":"NS Bridge · MARKET DATA\n",IsConnected()?"Terminal connected":"Terminal offline","\nUTC offset: ",DoubleToString(ServerUTCOffsetHours,2)," h\nLast publish: ",TimeToString(lastHeartbeat,TIME_SECONDS));
 busy=false;
}
