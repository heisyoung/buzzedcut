// Hold the show's composition through mobile keyboard open/close animations.
export function createStageLayout(width,height){
 let normal={width,height},editing=false,recoverUntil=0;
 return {
  compose(open,w,h,now){
   if(open&&!editing){if(Math.abs(w-normal.width)>30)normal={width:w,height:h};editing=true;recoverUntil=0;}
   else if(!open&&editing){editing=false;recoverUntil=now+1300;}
  },
  measure(w,h,now){
   if(Math.abs(w-normal.width)>30){normal={width:w,height:h};recoverUntil=0;}
   if(!editing&&now>=recoverUntil)normal={width:w,height:h};
   const stable=editing||now<recoverUntil;
   const height=stable?Math.max(h,normal.height):h;
   return {width:w,height,scale:Math.min(w/390,height/844),editing};
  }
 };
}
