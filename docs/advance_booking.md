This is requirement to update the code booking_utils.py for new requirement. 

step 1: click Advance booking instead of click current booking after entering the donation amount , take correct xpath from this html element 

<button id="adv" class="btn btn-act ng-scope" ng-if="(sdcc.pageDetails.amount &gt;= sdcc.pageDetails.advanceminAmount) &amp;&amp; (sdcc.pageDetails.amount &lt;= sdcc.pageDetails.advancemaxAmount)" ng-click="sdcc.Advancesrivani()">
					Advance Booking
				</button>

step 2: wait for another popup window appear, first check this checkbox

<input type="checkbox" id="ehpcept" name="ehpcept" ng-class="{chk_act:sripgc.timeSlotCheck===true}" ng-model="sripgc.timeSlotCheck" ng-click="sripgc.generalInstructions();" class="ng-pristine ng-untouched ng-valid">

step 3: then click Agreed button 

<button class="btn btn-act agreeBtn" style="padding-bottom:10px;" id="genag" ng-click="sripgc.okCovidClick();">Agreed</button>

step 4: after that in pilgrims page , check this checkbox 

<input type="checkbox" id="" value="checked" ng-model="sripgc.darshanCheck" ng-class="{chk_act:sripgc.darshanCheck===true}" ng-change="sripgc.clearAccomonDarshan();" class="ng-pristine ng-untouched ng-valid">

step 5: then click this date : 

<input type="text" class="form-control cal_icon ng-pristine ng-valid ng-touched" value="" name="date" id="darshanDate" ng-model="sripgc.selectedDarshandate" ng-click="sripgc.calenderDisplay('Break Darshan');" ng-disabled="sripgc.darshanCheck==false" ng-readonly="sripgc.darshanCheck==true" readonly="readonly">

step 6: now date selection window will open , pick the date based on the data updated in the
family in pilgrims_details.xlsx , column "Date" value is updated each family like 15-11-2026, 20-11-2026,  etc..

based on the value it should click the exact date from this date window. 

<calendar selected="item.day" id="cal3" select="sripgc.selectedDay(newItem,event)" selected-date="sripgc.selectedDarshandate" class="ng-isolate-scope">

<div class="header">
    <i class="fa fa-angle-left"></i>
    <span class="ng-binding">November 2026</span>
    <i class="fa fa-angle-right"></i>
</div>
<!--<div class="header" ng-if="$root.selLanguage=='English'">
    <i class="fa fa-angle-left"></i>
    <span>{{month.format("MMMM")}}   {{month.format("YYYY")}}</span>
    <i class="fa fa-angle-right"></i>
</div>-->
<!-- ngIf: $root.selLanguage=='Telugu' -->

<!-- ngIf: $root.selLanguage=='English' --><div class="week names ng-scope" ng-if="$root.selLanguage=='English'">
    <span class="day">Sun</span>
    <span class="day">Mon</span>
    <span class="day">Tue</span>
    <span class="day">Wed</span>
    <span class="day">Thu</span>
    <span class="day">Fri</span>
    <span class="day">Sat</span>
</div><!-- end ngIf: $root.selLanguage=='English' -->
<!-- ngIf: $root.selLanguage=='Kannada' -->
<!-- ngIf: $root.selLanguage=='Tamil' -->
<!-- ngIf: $root.selLanguage=='Hindi' -->
<!-- ngRepeat: week in weeks --><div class="week ng-scope" ng-repeat="week in weeks">
    <!-- ngRepeat: day in week.days --><span class="day 01-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">01</span><!-- end ngRepeat: day in week.days --><span class="day 02-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">02</span><!-- end ngRepeat: day in week.days --><span class="day 03-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">03</span><!-- end ngRepeat: day in week.days --><span class="day 04-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">04</span><!-- end ngRepeat: day in week.days --><span class="day 05-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">05</span><!-- end ngRepeat: day in week.days --><span class="day 06-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">06</span><!-- end ngRepeat: day in week.days --><span class="day 07-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">07</span><!-- end ngRepeat: day in week.days -->
</div><!-- end ngRepeat: week in weeks --><div class="week ng-scope" ng-repeat="week in weeks">
    <!-- ngRepeat: day in week.days --><span class="day 08-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">08</span><!-- end ngRepeat: day in week.days --><span class="day 09-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">09</span><!-- end ngRepeat: day in week.days --><span class="day 10-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">10</span><!-- end ngRepeat: day in week.days --><span class="day 11-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">11</span><!-- end ngRepeat: day in week.days --><span class="day 12-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">12</span><!-- end ngRepeat: day in week.days --><span class="day 13-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">13</span><!-- end ngRepeat: day in week.days --><span class="day 14-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">14</span><!-- end ngRepeat: day in week.days -->
</div><!-- end ngRepeat: week in weeks --><div class="week ng-scope" ng-repeat="week in weeks">
    <!-- ngRepeat: day in week.days --><span class="day 15-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">15</span><!-- end ngRepeat: day in week.days --><span class="day 16-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">16</span><!-- end ngRepeat: day in week.days --><span class="day 17-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">17</span><!-- end ngRepeat: day in week.days --><span class="day 18-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">18</span><!-- end ngRepeat: day in week.days --><span class="day 19-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">19</span><!-- end ngRepeat: day in week.days --><span class="day 20-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">20</span><!-- end ngRepeat: day in week.days --><span class="day 21-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">21</span><!-- end ngRepeat: day in week.days -->
</div><!-- end ngRepeat: week in weeks --><div class="week ng-scope" ng-repeat="week in weeks">
    <!-- ngRepeat: day in week.days --><span class="day 22-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">22</span><!-- end ngRepeat: day in week.days --><span class="day 23-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">23</span><!-- end ngRepeat: day in week.days --><span class="day 24-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">24</span><!-- end ngRepeat: day in week.days --><span class="day 25-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">25</span><!-- end ngRepeat: day in week.days --><span class="day 26-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">26</span><!-- end ngRepeat: day in week.days --><span class="day 27-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">27</span><!-- end ngRepeat: day in week.days --><span class="day 28-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">28</span><!-- end ngRepeat: day in week.days -->
</div><!-- end ngRepeat: week in weeks --><div class="week ng-scope" ng-repeat="week in weeks">
    <!-- ngRepeat: day in week.days --><span class="day 29-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">29</span><!-- end ngRepeat: day in week.days --><span class="day 30-11-2026 quotaNotReleased" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">30</span><!-- end ngRepeat: day in week.days --><span class="day 01-11-2026 different-month" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">01</span><!-- end ngRepeat: day in week.days --><span class="day 02-11-2026 different-month" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">02</span><!-- end ngRepeat: day in week.days --><span class="day 03-11-2026 different-month" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">03</span><!-- end ngRepeat: day in week.days --><span class="day 04-11-2026 different-month" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">04</span><!-- end ngRepeat: day in week.days --><span class="day 05-11-2026 different-month" ng-class="{ today: day.isToday, available:day.isAvailable, booked:day.isBooked, disabled:day.isDisabled, quotaNotReleased:day.isQuotaReleased, 'different-month': !day.isCurrentMonth, selected: day.date.isSame(selected)&amp;&amp;isClicked, highlight: day.date.isSame(selectedDate), blocked: day.isBlocked, freq: day.isFrequency, prevDay:day.isPreviousDay }" ng-click="select({newItem:day,event:$event})" ng-repeat="day in week.days">05</span><!-- end ngRepeat: day in week.days -->
</div><!-- end ngRepeat: week in weeks -->
</calendar>

step 7: Once date selected click ok button 

<button class="btn btn-act" id="calok" style="width: fit-content;" ng-click="sripgc.ClosePopUp();">OK</button>

step 8: start filling the pilgrims details - existing code  - > no captcha required for this flow so remove all the captcha related code in pilgirms page, also not timer will be running , remove timer running related code 

step 9: after filling all the pilgrims details cick continue

<button class="btn btn-act" id="sed_con" ng-click="sripgc.continueSubmit(userForm, userForm2,detailForm);sripgc.submitted=true;piligrimformSubmit=true;piligrimformSubmit2=true;submitted=true;">
					Continue
				</button>

step 10: Proceed with payment flow existing code. 

full html code for reference





                <div class="col-sm-12 cnt_new eseva sed_accomPilgrim" dynamic-height="" style="min-height: 376px;">
			<div class="back_cnt col-sm-12 mpr">
				❮❮ <span ng-click="sripgc.Back()" class="bk-lnk">Back</span>
			</div>
			
		<!--Change SED details starts below -->
		<!-- <div class="col-sm-12 usrinfo_cnt clearfix user_img cnt_hide">
			<span class="cnt_arwlft"></span>
			<figure ng-hide="sripgc.primaryImfFlag">
				<img src="{{sripgc.pageDetails.userData.userImageLocation}}" alt="user" width=70 height=70/>
			</figure>
			<section class="col-sm-9" id="prim_data">
				<div class="name">
					<strong ng-bind="sripgc.pageDetails.userData.piligrimFirstName"></strong>
				</div>
				<div class="row clearfix personal-details">
					<span class="col-md-2 col-sm-4col-xs-12 pull-left phone clearfix" ng-bind="sripgc.pageDetails.userData.piligrimPhoneMobile"></span>
					<span class="col-md-4 col-sm-6 col-xs-12 pull-left email clearfix" ng-bind="sripgc.pageDetails.userData.piligrimEmail"></span>
					<span class="col-md-4 col-sm-6 col-xs-12 pull-left pan clearfix" ng-show="{{sripgc.pageDetails.checkdonorPanNo}}">{{sripgc.pageDetails.userData.donorPanNo | uppercase}}</span>
					<span class="col-md-5 col-sm-12 col-xs-12 pull-left address clearfix">{{sripgc.pageDetails.userDetails.addr}}</span>
				</div>
			</section>
		</div> -->
		
		<!--<div class="col-sm-12 usrinfo_cnt clearfix mtp10 " ng-show='sripgc.pageDetails.userData.donorJointUserFlag'>
			<figure ng-hide="sripgc.jointImfFlag">
				<img ng-src={{sripgc.pageDetails.jointUserImg}} alt="joint donor" height="70" width="70">
			</figure>
			<section class="col-sm-9 col-xs-8 joint_boxinfo donor_jointpay" id="joint_data">
				<div class="col-md-12 row joint">
					Joint Donor
				</div>
				<div class="name bdr0 joint_info">
					<strong>{{sripgc.pageDetails.userData.donorName}}</strong>
					<span class="phone">{{sripgc.pageDetails.userData.donorMobileNo}}</span>
					<span class='pan' ng-show="{{sripgc.pageDetails.checkJointDonorPANId}}">{{sripgc.pageDetails.userData.jointDonorPanId | uppercase}}</span>
				</div>
			</section>
		</div>-->
		
		<!-- <div class="col-sm-12 usrinfo_cnt clearfix pay_details" style="padding-bottom: 0px;">
			<strong class="col-xs-11 col-sm-12 mbtm10 mpr row_clear"> {{sripgc.pageDetails.userData.trustName}} </strong>
			<div class="col-xs-11 col-sm-12 mbtm10 mpr row_clear">
				<span>Amount</span>
				<strong > Rs.{{sripgc.pageDetails.userData.offeringAmount}} </strong>
			</div>
			
			<div class="col-xs-11 col-sm-12 mbtm10 mpr row_clear">
				<span ng-show="sripgc.pageDetails.userData.onBehalfOf" >On Behalf of</span>
				<strong ng-bind="sripgc.pageDetails.userData.onBehalfOf"></strong>
			</div>
		</div> -->
		
		<!-- select darshan and accom dates starts here -->	
		<div class="col-sm-12 usrinfo_cnt redeem_checkavil clearfix pay_details" style="padding-bottom: 0px;">
			<!-- break darshan start -->	
			<div class="clearfix dash">
				<div class="col-md-1 col-sm-1 col-xs-1 donor_mlpd0 redeem_checkcell redeem_check pdrgt0">
					<div class="redeem_chk">
						<span class="chk_cnt">
								<input type="checkbox" id="" value="checked" ng-model="sripgc.darshanCheck" ng-class="{chk_act:sripgc.darshanCheck===true}" ng-change="sripgc.clearAccomonDarshan();" class="ng-valid ng-dirty ng-valid-parse chk_act ng-touched">
								<label></label>
						</span>	
					</div>	
				</div>
				
				<div class="col-sm-2 col-xs-6 donor_mlpd0 donor_mrpd0 text-center redeem_checkcell redeem_service">			
					<i class="dms dms-ttd_darshan"></i>
					<span>Break Darshan</span>
				</div>
				
				<div class="col-md-2 col-sm-12 col-xs-5 donor_mlpd0 donor_mrpd0 break_date">
					<label class="control-label" for="inputLarge">Date</label>
					<input type="text" class="form-control cal_icon ng-pristine ng-valid ng-touched" value="" name="date" id="darshanDate" ng-model="sripgc.selectedDarshandate" ng-click="sripgc.calenderDisplay('Break Darshan');" ng-disabled="sripgc.darshanCheck==false" ng-readonly="sripgc.darshanCheck==true" readonly="readonly">
					<div class="err mtop6" ng-show="sripgc.submitted &amp;&amp; sripgc.darshanCheck &amp;&amp; !sripgc.selectedDarshandate">Please select the date</div>
				</div>	
				
				<div class="col-sm-2 col-xs-12 donor_clear donor_mlpd0 redeem_checktime pdlft0 pdrgt0" style="width: 13%;">
					<p style=" margin-left: 35px;">Reporting Time</p>
					<span>
						<ul>
							<li style="margin-left:45px; margin-top: 10px;" class="ng-binding"></li>
						</ul>
						
					</span>					
				</div>
				
				<div class="col-sm-2 col-xs-12 donor_clear donor_mlpd0 redeem_checktime pdlft0 pdrgt0">
					<p style=" margin-left: 35px;">Reporting Location</p>
					<span>
						<ul>
							<li style="margin-left:45px; margin-top: 10px;" class="ng-binding"></li>
						</ul>
						
					</span>					
				</div>
				
				<div class="form-group col-md-2 col-sm-12 col-xs-5 donor_mlpd0 donor_mrpd0 break_date1">
					<label class="control-label" for="inputLarge">No. of Additional Laddus</label>
					<form name="sripgc.darshanForm" novalidate="" class="ng-pristine ng-valid ng-valid-min ng-valid-max">
						<input type="number" class="form-control  mrt5 ng-pristine ng-untouched ng-valid ng-valid-min ng-valid-max" min="1" max="999" ng-max="999" ng-model="sripgc.extraLaddus" ng-disabled="sripgc.darshanCheck==false" name="addladdus" id="addladdus" onpaste="return false" ng-keypress="sripgc.key($event)">
					
						<div class="">(₹ 50 per Laddu)</div>
						
						<div class="err mtop6">
							<span ng-show="sripgc.submitted  || (sripgc.darshanForm.addladdus.$dirty &amp;&amp; sripgc.darshanForm.addladdus.$invalid)" class=""> 
								<span ng-show="(sripgc.darshanForm.addladdus.$error.min || sripgc.darshanForm.addladdus.$error.max )&amp;&amp; sripgc.darshanForm.addladdus.$error" class="ng-hide">Minimum of 1 and Maximum of 999 Laddus are accepted </span>
							</span>
						</div>
					</form>
				</div>
				
					 
				<div class="col-sm-2 col-xs-12 donor_clear donor_mlpd0 redeem_checktime pdlft0 pdrgt0" style="width: 13%; padding-left: 30px !important;">
					<label class="control-label" for="inputLarge" style="font-weight:bold;">Darshan Cost<span style="font-weight:normal;">  (per person)</span></label>
					<span>
						<ul>
							<li class="ng-binding"> ₹ 500</li>
						</ul>
					</span>					
				</div>
			</div>
			<!-- break darshan end -->
			
			<!-- Accommodation start -->
			<!-- ngIf: sripgc.pageDetails.selectedOptions.noOfPersons > 1 && sripgc.darshanCheck --><div class="clearfix ng-scope" style="padding-top: 20px; border-top: 1px dotted #A50509;" ng-if="sripgc.pageDetails.selectedOptions.noOfPersons &gt; 1 &amp;&amp; sripgc.darshanCheck">
				<div class="col-md-1 col-sm-1 col-xs-1 donor_mlpd0 redeem_checkcell redeem_check pdrgt0">
					<div class="redeem_chk">
						<span class="chk_cnt">
							<input type="checkbox" id="" ng-disabled="(sripgc.selectedDarshandate=='' || sripgc.selectedDarshandate==undefined)" value="checked" ng-model="sripgc.accomCheck" ng-class="{chk_act:sripgc.accomCheck===true}" ng-click="sripgc.checknominees()" ng-change="sripgc.clearAccomData();" class="ng-pristine ng-untouched ng-valid" disabled="disabled">
							<label></label>
						</span>	
					</div>	
				</div>
				
				<div class="col-sm-2 col-xs-6 donor_mlpd0 donor_mrpd0 text-center redeem_checkcell redeem_service">			
					<i class="dms dms-ttd_acc"></i>
					<span><p>Accommodation</p><p class="text-danger"></p><p class="text-danger"></p></span>
				</div>
				
				<div class="form-group col-md-2 col-sm-2 col-xs-5 donor_mlpd0 donor_mrpd0">
					<label class="control-label" for="inputLarge">Date</label>
	
					<input type="text" class="form-control cal_icon ng-pristine ng-untouched ng-valid" ng-click="sripgc.calenderDisplay('Accommodation');" ng-model="sripgc.selectedAccdate" id="accomodationDate" ng-disabled="sripgc.accomCheck==false" name="sdonredatefrom" ng-readonly="sripgc.accomCheck==true" disabled="disabled">
					<div class="err ng-hide" ng-show="sripgc.submitted &amp;&amp; sripgc.accomCheck &amp;&amp; !sripgc.selectedAccdate">
						Please select the date.
					</div>
				</div>
			
				<div class="form-group col-md-2 col-sm-2 col-xs-5">
					<label class="control-label" for="inputLarge" style="margin-left: 35px;">No. of Days<sup class="text-danger">*</sup></label>
					<p style="margin-left: 61px;margin-top: 10px;">01</p>
				</div>
					
				<div class="form-group col-md-1 col-sm-1 col-xs-5">
					<label class="control-label" for="inputLarge" style="margin-left: 23px;">Tariff<sup class="text-danger">*</sup></label>
					<p style="margin-left: 23px;margin-top: 10px;" class="ng-binding">₹ </p>
				</div>
				
				<div class="form-group col-md-1 col-sm-1 col-xs-5">
					<label class="control-label" for="inputLarge" style="margin-left: 35px;">Caution Deposit<sup class="text-danger">*</sup></label>
					<p style="margin-left: 33px;margin-top: 10px;" class="ng-binding">₹ </p>
				</div>
				
				<div class="form-group col-md-3 col-sm-3 col-xs-5">
					<label class="control-label" for="inputLarge" style="margin-left: 35px;">Check-in Time Slot<sup class="text-danger">*</sup></label>
					<p style="margin-left: 35px;margin-top: 10px;" class="ng-binding"></p>
					<div class="err ng-hide" ng-show="sripgc.submitted &amp;&amp; sripgc.accomCheck &amp;&amp; !sripgc.checkInTimeSlot" style="padding-top: 30px;">
						Please select the Check-in Time Slot.
					</div>
				</div>
			</div><!-- end ngIf: sripgc.pageDetails.selectedOptions.noOfPersons > 1 && sripgc.darshanCheck -->
			<!-- Accommodation end -->
		</div>
		<!-- select darshan and accom dates starts here -->	
		
		<!-- Pilgrim Details starts here -->
		<!-- ngIf: sripgc.showAccompanyingPilgrim --><div class="col-md-12 pdlft0 sed_gridtitle ng-scope" ng-if="sripgc.showAccompanyingPilgrim">
			<h5>Pilgrim Details <span style="font-weight: 500;font-size: 15px;">(Only the pilgrims added here will be eligible for Darshan)</span> </h5>	
		</div><!-- end ngIf: sripgc.showAccompanyingPilgrim -->

		<!-- SED Grid starts here -->
		<!-- ngIf: sripgc.showAccompanyingPilgrim --><div class="table_sedGrid ng-scope" ng-if="sripgc.showAccompanyingPilgrim">
			<div class="table_tr table_th">
				<div class="table_td">S.No</div>
				<div class="table_td">Name (As per ID Proof)<sup class="text-danger">*</sup></div>
				<div class="table_td" style="width: 11%;">Age<sup class="text-danger">*</sup></div>
				<div class="table_td">Gender<sup class="text-danger">*</sup></div>
				<div class="table_td">ID Proof Type<sup class="text-danger">*</sup></div>
				<div class="table_td">ID Proof Number<sup class="text-danger">*</sup></div>
			</div>
		</div><!-- end ngIf: sripgc.showAccompanyingPilgrim -->
		
		<!-- self user-->
		<!-- <form autocomplete="off" name="detailForm" novalidate="" role="form" class="table_sedGrid" ng-show="sripgc.pageDetails.selectedOptions.self">
			<div class="table_tr table_trPrimary" ng-show="sripgc.pageDetails.selectedOptions.self">
				<div class="table_td">1</div>
				<div class="table_td removeName"></div>
				<div class="table_td"><strong>{{sripgc.pageDetails.userFullname()}}</strong></div>
				<div class="table_td">{{sripgc.pageDetails.userDetails.age}}</div>
				<div class="table_td">{{sripgc.pageDetails.userDetails.gender}}</div>
				<div class="table_td hide_proof">{{sripgc.pageDetails.userDetails.selectedProof}}</div>	
				<div class="table_td hide_proof">{{sripgc.pageDetails.userDetails.userProofID.toUpperCase()}}</div>	
				<div class="table_td hide_proof">
					<div class="text-center edit edit_new mrg0" id="editid" >
						<span class="edit_sed" ng-click="sripgc.onClickchangedetails();submitted=false"></span>
					</div>
				</div>	
				
				<div class="table_td changedetails">
					<div class="form-group min_height40 mrg0">
						<select name="proofSself" class="form-control"
						ng-model="sripgc.pageDetails.selectedProofs"
						ng-options="cnt.id as cnt.type for cnt in sripgc.proofTypes"
						ng-change="sripgc.validationproofId('s')" required>

							<option class="control-label" value="">Select </option>
						</select>
						<div class="help-block err">
							<span ng-show="submitted  || (detailForm.proofSself.$dirty && detailForm.proofSself.$invalid)"> 
								<span ng-show="detailForm.proofSself.$error.required">Please select ID Proof type</span> 
								<span ng-show="detailForm.proofSself.$error.pattern">Please select ID Proof type</span> 
							</span>
						</div>

					</div>
				</div>

				<div class="table_td changedetails">
					<div class="form-group min_height40 mrg0">
						<span id="testings"></span>
						<input type="text" class="form-control" name="proofIds"  id="proofIds" ng-model="sripgc.pageDetails.photoIds" ng-pattern ="sripgc.pageDetails.regexs"  ng-change="validateProofs('s')" placeholder="Enter ID Card Number"  required />
						<div class="help-block err">
							<span ng-show="submitted  || (detailForm.proofIds.$dirty && detailForm.proofIds.$invalid)"> 
								<span ng-show="detailForm.proofIds.$error.required || sripgc.pageDetails.photoIds=='' ">{{multiLanguageData['DP.idcardcontbeempty']}}</span> 
								<span ng-show="detailForm.proofIds.$error.pattern">{{sripgc.pageDetails.patterns}}</span> 
								<div  ng-show="detailForm.proofIds.$error.verhoeff && !detailForm.proofIds.$error.pattern && !detailForm.proofIds.$error.required">Invalid Aadhaar Number</div>
							<div ng-show="detailForm.proofIds.$error.proofTypeMissing">Please select ID Proof type</div>
							</span>
						</div>

					</div>
				</div>
				
				<div class="table_td edit_save mrg0 changedetails" ng-hide='sripgc.checkOthers("yes")'>
					<button title="Save" class="btn btn-act sedpilgrim_save" id="sedpilgrim_save" ng-click="sripgc.Save(detailForm);submitted=true">
						Save
					</button>

					<button title="Cancel" class="btn btn-act sedpilgrim_cancel" id="sedpilgrim_cancel" ng-click="sripgc.Cancel1()">
					Cancel
					</button>
				</div>
			</div>
		</form>	 -->
		<!-- End self user -->	

	<!-- Other primary user -->
	<form autocomplete="off" role="form" name="userForm" id="othersForm" class="ng-pristine table_sedGrid ng-invalid ng-invalid-required ng-valid-pattern ng-valid-minlength ng-valid-maxlength ng-valid-min ng-valid-max" ng-show="!sripgc.pageDetails.selectedOptions.self &amp;&amp; sripgc.showAccompanyingPilgrim">
		<div class="table_tr" id="primaryPilgrim">
			<div class="table_td" style="width: 52px;">1</div>
		
			<div class="table_td" style="width: 100px;">
				<div class="form-group">
					<input class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required ng-valid-pattern ng-valid-minlength ng-valid-maxlength" ng-model="sripgc.pageDetails.fName0" name="fName0" ng-minlength="4" ng-maxlength="80" ng-pattern="/^[a-zA-Z ]*$/" required="" type="text" placeholder="Enter Name">

					<div class="help-block err">
						<span class="" ng-show="piligrimformSubmit  || (userForm.fName0.$dirty &amp;&amp; userForm.fName0.$invalid)"> <span ng-show="userForm.fName0.$error.required ">Pilgrim Name cannot be empty </span> <span ng-show="userForm.fName0.$error.minlength || userForm.fName0.$error.maxlength || userForm.fName0.$error.pattern" class="ng-hide">Please enter valid Pilgrim Name</span> </span>
					</div>

				</div>
			</div>
			
			<div class="table_td" style="width: 11%;">
				<div class="form-group">
					<input type="number" class="form-control ng-pristine ng-untouched ng-valid-min ng-valid-max ng-invalid ng-invalid-required ng-valid-pattern" ng-model="sripgc.pageDetails.age0" name="age0" min="0" ng-min="10" ng-max="120" ng-change="sripgc.setProofTypes(sripgc.pageDetails.age0, 0)" ng-pattern="/^\d*$/" required="" onpaste="return false" placeholder="Enter Age" ng-keypress="sripgc.keyage($event)">

					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm.age0.$dirty &amp;&amp; userForm.age0.$invalid)" class=""> <span ng-show="userForm.age0.$error.required">Please enter age</span> <span class="mbtm10 ng-hide" ng-show="userForm.age0.$error.min || userForm.age0.$error.max || userForm.age0.$error.pattern">The valid age allowed  is 10 to 120 years</span>
					</span></div>

				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40">
					<select class="form-control ng-pristine ng-untouched ng-valid" ng-model="sripgc.pageDetails.gender0" name="gender0">
						<option value="Male">Male</option>
						<option value="Female">Female</option>
						<option value="Transgender">Transgender</option>
					</select>
					<div class="help-block err">
						<span class="" ng-show="piligrimformSubmit  || (userForm.gender0.$dirty &amp;&amp; userForm.gender0.$invalid)"> <span ng-show="userForm.gender0.$error.required " class="ng-hide">Gender cannot be empty</span>
					</span></div>

				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40">
					<select name="proofS0" class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required" ng-model="sripgc.pageDetails.selectedProof0" id="selectedProof0" ng-options="cnt.id as cnt.type for cnt in sripgc.proofTypes0" ng-change="sripgc.validationproofId(0)" required=""><option class="control-label" value="" selected="selected"> Select </option></select>
					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm.proofS0.$dirty &amp;&amp; userForm.proofS0.$invalid)" class=""> 
							<span ng-show="userForm.proofS0.$error.required">Please select ID Proof type</span> 
							<span ng-show="userForm.proofS0.$error.pattern" class="ng-hide">Please select valid ID Proof type</span> 
						</span>
					</div>
				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40 mmr">
					<span id="testing0"></span>
					<input type="text" class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required ng-valid-pattern" name="proofId0" id="proofId0" ng-model="sripgc.pageDetails.photoId0" placeholder="Enter ID Card Number" ng-change="validateProof(0)" required="">

					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm.proofId0.$dirty &amp;&amp; userForm.proofId0.$invalid)" class=""> 
							<span ng-show="userForm.proofId0.$error.required || sripgc.pageDetails.photoId0=='' ">ID Proof Number cannot be empty</span> 
							<span ng-show="userForm.proofId0.$error.pattern" class="ng-binding ng-hide"></span> 
							<div ng-show="userForm.proofId0.$error.verhoeff &amp;&amp; !userForm.proofId0.$error.pattern &amp;&amp; !userForm.proofId0.$error.required" class="ng-hide">Invalid Aadhaar Number</div>
							<div ng-show="userForm.proofId0.$error.proofTypeMissing" class="ng-hide">Please select ID Proof type</div>
						</span>
					</div>
				</div>
			</div>
			
		</div>
	</form>
	<!-- End  Other primary user -->

	<!-- Accomponying pilgrim -->
	<form autocomplete="off" role="form" name="userForm2" id="othersForm2" class="ng-pristine table_sedGrid ng-invalid ng-invalid-required ng-valid-pattern ng-valid-maxlength ng-valid-min ng-valid-max" ng-show="sripgc.showAccompanyingPilgrim">
		<!-- ngRepeat: person in sripgc.persons track by $index --><!-- ngIf: sripgc.persons.length!==0 --><div class="table_tr ng-scope" ng-repeat="person in sripgc.persons track by $index" ng-if="sripgc.persons.length!==0">
			<div class="table_td ng-binding" ng-style="(selLanguage=='Tamil'?{'width': '76px'}:'')">2</div>
		
			<div class="table_td">
				<div class="form-group">
					<input class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required ng-valid-pattern ng-valid-maxlength" ng-model="sripgc.pageDetails['fName'+($index+1)]" placeholder="Enter Name" name="fName1" ng-maxlength="80" ng-pattern="/^[a-zA-Z ]*$/" required="" type="text">
					<div class="help-block err">
						<span class="" ng-show="piligrimformSubmit  || (userForm2.fName1.$dirty &amp;&amp; userForm2.fName1.$invalid)"> <span ng-show="userForm2.fName1.$error.required">Pilgrim Name cannot be empty</span> <span class="ng-hide" ng-show="userForm2.fName1.$error.maxlength || userForm2.fName1.$error.pattern">Please enter valid Pilgrim Name</span> </span>
					</div>

				</div>
			</div>
			
			<div class="table_td" style="width: 11%;">
				<div class="form-group">
					<input type="number" class="form-control ng-pristine ng-untouched ng-valid-min ng-valid-max ng-invalid ng-invalid-required ng-valid-pattern" ng-model="sripgc.pageDetails['age'+($index+1)]" name="age1" min="0" ng-min="10" ng-max="120" ng-change="sripgc.setProofTypes(sripgc.pageDetails['age'+($index+1)], $index+1)" ng-pattern="/^\d*$/" onpaste="return false" placeholder="Enter Age" required="" ng-keypress="sripgc.keyage($event)">

					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm2.age1.$dirty &amp;&amp; userForm2.age1.$invalid)" class=""> <span ng-show="userForm2.age1.$error.required">Please enter age</span> <span class="mbtm10 ng-hide" ng-show="userForm2.age1.$error.min || userForm2.age1.$error.max || userForm2.age1.$error.pattern">The valid age allowed  is 10 to 120 years</span>
					</span></div>

				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40">
					<select class="form-control ng-pristine ng-untouched ng-valid" ng-model="sripgc.pageDetails['gender'+($index+1)]" name="gender1">
						<option value="Male">Male</option>
						<option value="Female">Female</option>
						<option value="Transgender">Transgender</option>
					</select>
					<div class="help-block err">
						<span class="" ng-show="piligrimformSubmit  || (userForm2.gender.$dirty &amp;&amp; userForm2.genderName.$invalid)"> <span ng-show="userForm2.gender1.$error.required" class="ng-hide">Gender cannot be empty</span> </span>
					</div>
				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40">
					<select name="proofS1" class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required" ng-model="sripgc.pageDetails['selectedProof'+($index+1)]" id="['selectedProof'+($index+1)]" ng-options="cnt.id as cnt.type for cnt in sripgc['proofTypes'+($index+1)]" ng-change="sripgc.validationproofId($index+1)" required=""><option class="control-label" value="" selected="selected">Select </option></select>
					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm2.proofS1.$dirty &amp;&amp; userForm2.proofS1.$invalid)" class=""> 
							<span ng-show="userForm2.proofS1.$error.required">Please select ID Proof type</span> 
							<span ng-show="userForm2.proofS1.$error.pattern" class="ng-hide">Please select valid ID proof type</span> 
						</span>
					</div>

				</div>
			</div>
			
			<div class="table_td">
				<div class="form-group min_height40">
					<span id="testing1"></span>
					<input type="text" class="form-control ng-pristine ng-untouched ng-invalid ng-invalid-required ng-valid-pattern" name="proofId1" id="proofId1" ng-model="sripgc.pageDetails['photoId'+($index+1)]" placeholder="Enter ID Card Number" ng-change="validateProof1($index+1)" required="">

					<div class="help-block err">
						<span ng-show="piligrimformSubmit  || (userForm2.proofId1.$dirty &amp;&amp; userForm2.proofId1.$invalid)" class=""> 
							<span ng-show="userForm2.proofId1.$error.required &amp;&amp; !userForm2.proofId1.$error.pattern">ID Proof Number cannot be empty</span> 
							<span ng-show="userForm2.proofId1.$error.pattern" class="ng-binding ng-hide"></span> 
							<div ng-show="userForm2.proofId1.$error.verhoeff &amp;&amp; !userForm2.proofId1.$error.pattern &amp;&amp; !userForm2.proofId1.$error.required" class="ng-hide">Invalid Aadhaar Number</div>
							<div ng-show="userForm2.proofId1.$error.proofTypeMissing" class="ng-hide">Please select ID Proof type</div>
						</span>
					</div>

				</div>
			</div>
		
		</div><!-- end ngIf: sripgc.persons.length!==0 --><!-- end ngRepeat: person in sripgc.persons track by $index -->
	</form>
	<!-- End accomponying pilgrim -->
	<!-- Pilgrim Details end here -->

			
		<!-- Eligibility Error Message-START -->
		<div class="err cal_err ng-hide" ng-show="sripgc.EligibilityError">
			<p class="ng-binding">
				 
			</p>
			<p class="ng-binding">
				
			</p>
			<p class="ng-binding">
				
			</p>
		</div>
		<!-- Eligibility Error Message-END -->
		
		<!-- Duplicate Error Message-START -->
		<div class="err cal_err ng-hide" ng-show="sripgc.DuplicateError">
			<p class="ng-binding">
				
			</p>
		</div>
		<!-- Duplicate Error Message-END -->
		
		<div class="err cal_err ng-hide" ng-show="sripgc.AccomEligibilityError">
			<p class="ng-binding"></p>
		</div>
		
		<!-- Kalyanotsavam Error Message-START -->
		<div class="err cal_err ng-hide" ng-show="sripgc.sedError">
			<p class="ng-binding"></p>
		</div>
		<!-- Kalyanotsavam Error Message-END -->
		
		<div class="err cal_err ng-hide" ng-show="sripgc.aadharError">
			<p class="ng-binding">
				
			</p>
		</div>
			
		<div class="row">
		 <!--<div class="clear col-md-12" ng-show="sripgc.isAadharSelected">
					<div class="guide_check">
						<div class="guide_pos">
							<input type="checkbox" name="accept" ng-class="{chk_act:sripgc.aadharSelected===true}" ng-model="sripgc.aadharSelected"> <label></label>
						</div>
						<div style="padding-top: 21px;vertical-align: middle; padding-left: 26px;" class="ng-binding">
							 I hereby authorize TTD to use Aadhar Number for verification purpose. 
						</div>					
					</div>
					<div class="err help-block mtop6 col-xs-12 pdlft0 ng-hide" ng-show="sripgc.aadharSelectedErrFlag">
						<span class="ng-binding">Please agree to continue.</span>
					</div>				
				</div> -->
				
			<div class="col-md-8 mobile_bottom15" style="margin-top:25px">
					<strong class="ng-binding"></strong>
					<ul class="col-md-12 nav">
						<li></li>
						<li class="ng-binding">
							 <sup class="text-danger-note"></sup>
						</li>
						<li></li>
					</ul>			
				<!--Click on Continue confirms your acceptance to the <a class="terms" ng-click="bdc.TermsPopup()">Terms and Conditions </a-->
			</div>
			
			<div class="text-right col-md-4" style="margin-top: 21px;">
				<button class="btn" id="sedpiligrim_cancel" ng-click="sripgc.Reset()">
					Reset
				</button>
				<button class="btn btn-act" id="sed_con" ng-click="sripgc.continueSubmit(userForm, userForm2,detailForm);sripgc.submitted=true;piligrimformSubmit=true;piligrimformSubmit2=true;submitted=true;">
					Continue
				</button>
			</div>
			
			<div class="col-md-12 col-sm-12 note_lst note_lst_donate row" style="margin-left: 5px; width: auto;">
				<strong>Note:</strong>
				<ol>
					<!-- ngIf: sripgc.pageDetails.selectedOptions.noOfPersons > 1 --><li class="mrg0 ng-scope" style="font-weight: bold;" ng-if="sripgc.pageDetails.selectedOptions.noOfPersons &gt; 1"> Caution deposit of Rs. 1000/- will be collected for accommodation at Donor Counter in CRO Office, Tirumala for amount between Rs. 20000/-  and Rs. 99999/-. </li><!-- end ngIf: sripgc.pageDetails.selectedOptions.noOfPersons > 1 -->
					<li class="mrg0">Click on Continue authorizes TTD to use Aadhaar Number or Passport Number for verification purpose.</li>
				</ol>
			</div>
			
		</div>
		</div>